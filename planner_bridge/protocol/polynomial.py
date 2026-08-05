from __future__ import annotations

import math
from typing import Any

import numpy as np


def evaluate(coefficients: list[float], u: float, derivative: int, duration: float) -> float:
    """Evaluate AM-Planner's descending-power normalized polynomial."""
    order = len(coefficients) - 1
    total = 0.0
    for index, coefficient in enumerate(coefficients):
        power = order - index
        if power < derivative:
            continue
        multiplier = math.prod(range(power - derivative + 1, power + 1)) if derivative else 1
        total += float(coefficient) * multiplier * u ** (power - derivative)
    return total / duration**derivative


def physics_time_grid(total_duration: float, physics_dt: float = 1.0 / 240.0) -> np.ndarray:
    """Return ``min(k*physics_dt,total_duration)`` with one final sample."""
    total = float(total_duration)
    dt = float(physics_dt)
    if not math.isfinite(total) or total <= 0.0 or not math.isfinite(dt) or dt <= 0.0:
        raise ValueError("total_duration and physics_dt must be finite and positive")
    count = int(math.ceil(total / dt))
    times = np.asarray([min(k * dt, total) for k in range(count + 1)], dtype=float)
    if times[-1] != total:
        times = np.concatenate([times, np.asarray([total], dtype=float)])
    if len(times) > 1 and not np.all(np.diff(times) > 0.0):
        raise ValueError("physics time grid must be strictly increasing")
    return times


def _segment_at_time(t: float, durations: np.ndarray) -> tuple[int, float]:
    total = float(np.sum(durations))
    bounded = min(max(float(t), 0.0), total)
    cumulative = np.cumsum(durations)
    segment = min(int(np.searchsorted(cumulative, bounded, side="left")), len(durations) - 1)
    start = float(cumulative[segment] - durations[segment])
    local = min(max(bounded - start, 0.0), float(durations[segment]))
    return segment, local / float(durations[segment])


def evaluate_message(payload: dict[str, Any], times: np.ndarray | list[float]) -> dict[str, np.ndarray]:
    """Evaluate raw trajectory polynomials at arbitrary monotonic times."""
    msg = payload["message"]
    orders = [int(value) for value in msg["order"]]
    durations = np.asarray(msg["time"], dtype=float)
    if len(durations) == 0 or not np.isfinite(durations).all() or np.any(durations <= 0.0):
        raise ValueError("trajectory segment durations must be finite and positive")
    sample_times = np.asarray(times, dtype=float)
    total = float(np.sum(durations))
    if sample_times.ndim != 1 or not np.isfinite(sample_times).all():
        raise ValueError("times must be a finite one-dimensional array")
    if len(sample_times) and (sample_times[0] < -1e-12 or sample_times[-1] > total + 1e-12):
        raise ValueError("times must lie within the raw trajectory duration")
    rows = {name: np.zeros((len(sample_times), 3), dtype=float) for name in ("position", "velocity", "acceleration", "jerk")}
    rows["segment_id"] = np.zeros(len(sample_times), dtype=int)
    for row, time in enumerate(sample_times):
        segment, u = _segment_at_time(float(time), durations)
        order = orders[segment]
        offset = sum(previous + 1 for previous in orders[:segment])
        rows["segment_id"][row] = segment
        for axis_index, axis in enumerate(("x", "y", "z")):
            coefficients = msg[f"coef_{axis}"][offset : offset + order + 1]
            for name, derivative in (("position", 0), ("velocity", 1), ("acceleration", 2), ("jerk", 3)):
                rows[name][row, axis_index] = evaluate(coefficients, u, derivative, float(durations[segment]))
    rows["time"] = sample_times.copy()
    rows["phase_progress"] = sample_times / total
    return rows


def sample_message(payload: dict[str, Any], sample_hz: float = 200.0) -> dict[str, np.ndarray]:
    if sample_hz <= 0 or not math.isfinite(sample_hz):
        raise ValueError("sample_hz must be finite and positive")
    total = float(np.sum(np.asarray(payload["message"]["time"], dtype=float)))
    dt = 1.0 / float(sample_hz)
    count = int(math.floor(total / dt + 1e-12))
    times = np.arange(count + 1, dtype=float) * dt
    if not len(times) or not math.isclose(float(times[-1]), total, abs_tol=dt * 1e-9, rel_tol=0.0):
        times = np.append(times, total)
    return evaluate_message(payload, times)
