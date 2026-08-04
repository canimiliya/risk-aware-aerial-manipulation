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


def sample_message(payload: dict[str, Any], sample_hz: float = 200.0) -> dict[str, np.ndarray]:
    if sample_hz <= 0 or not math.isfinite(sample_hz):
        raise ValueError("sample_hz must be finite and positive")
    msg = payload["message"]
    orders = [int(v) for v in msg["order"]]
    durations = np.asarray(msg["time"], dtype=float)
    total = float(durations.sum())
    dt = 1.0 / sample_hz
    times = np.arange(0.0, total, dt, dtype=float)
    if len(times) == 0 or not np.isclose(times[-1], total, atol=dt * 1e-9, rtol=0.0):
        times = np.append(times, total)
    cumulative = np.cumsum(durations)
    result = {key: np.zeros((len(times), 3), dtype=float) for key in ("position", "velocity", "acceleration")}
    result.update({"time": times, "segment_id": np.zeros(len(times), dtype=int), "phase_progress": times / total})
    for row, t in enumerate(times):
        segment = min(int(np.searchsorted(cumulative, t, side="left")), len(durations) - 1)
        local = min(max(t - float(cumulative[segment] - durations[segment]), 0.0), float(durations[segment]))
        u = local / float(durations[segment])
        offset = sum(order + 1 for order in orders[:segment])
        result["segment_id"][row] = segment
        for axis_index, axis in enumerate(("x", "y", "z")):
            coefficients = msg[f"coef_{axis}"][offset : offset + orders[segment] + 1]
            for name, derivative in (("position", 0), ("velocity", 1), ("acceleration", 2)):
                result[name][row, axis_index] = evaluate(coefficients, u, derivative, float(durations[segment]))
    return result
