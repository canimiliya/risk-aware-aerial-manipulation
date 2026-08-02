"""Source-grounded sampling for quadrotor_msgs/PolynomialTrajectory.

The AM-Planner message contains normalized position coefficients. The source
evaluates them as descending powers of u in [0, 1], and divides first-,
second-, and third-order derivatives by duration, duration**2, and
duration**3 respectively. This module mirrors that contract without ROS.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


EXPORTER_VERSION = "s1-r2-exporter-1.0"
MESSAGE_TYPE = "quadrotor_msgs/PolynomialTrajectory"


def load_captured_message(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("message_type") != MESSAGE_TYPE:
        raise ValueError(f"unexpected message type in {path}: {payload.get('message_type')}")
    return payload


def message_contract(payload: dict[str, Any]) -> dict[str, Any]:
    msg = payload["message"]
    orders = [int(value) for value in msg["order"]]
    durations = [float(value) for value in msg["time"]]
    expected_coefficients = sum(order + 1 for order in orders)
    actual_coefficients = {name: len(msg[f"coef_{name}"]) for name in ("x", "y", "z")}
    return {
        "message_type": payload["message_type"],
        "frame_id": msg.get("header", {}).get("frame_id", ""),
        "num_segment": int(msg["num_segment"]),
        "orders": orders,
        "durations": durations,
        "expected_coefficients_per_axis": expected_coefficients,
        "actual_coefficients_per_axis": actual_coefficients,
        "total_duration": float(sum(durations)),
    }


def _axis_coefficients(msg: dict[str, Any], segment: int, axis: str) -> np.ndarray:
    orders = [int(value) for value in msg["order"]]
    offset = sum(order + 1 for order in orders[:segment])
    count = orders[segment] + 1
    return np.asarray(msg[f"coef_{axis}"][offset : offset + count], dtype=np.float64)


def _evaluate(coefficients: np.ndarray, u: float, derivative: int, duration: float) -> float:
    order = len(coefficients) - 1
    value = 0.0
    for index, coefficient in enumerate(coefficients):
        power = order - index
        if power < derivative:
            continue
        multiplier = math.prod(range(power - derivative + 1, power + 1)) if derivative else 1
        value += coefficient * multiplier * (u ** (power - derivative))
    return value / (duration ** derivative)


def sample_message(payload: dict[str, Any], sample_dt: float = 0.01) -> dict[str, np.ndarray]:
    if sample_dt <= 0 or not math.isfinite(sample_dt):
        raise ValueError("sample_dt must be finite and positive")
    msg = payload["message"]
    orders = [int(value) for value in msg["order"]]
    durations = np.asarray(msg["time"], dtype=np.float64)
    if len(orders) != int(msg["num_segment"]) or len(durations) != int(msg["num_segment"]):
        raise ValueError("num_segment does not match order/time lengths")
    if np.any(~np.isfinite(durations)) or np.any(durations <= 0):
        raise ValueError("segment durations must be finite and positive")
    total = float(durations.sum())
    times = np.arange(0.0, total, sample_dt, dtype=np.float64)
    if len(times) == 0 or not np.isclose(times[-1], total, rtol=0.0, atol=sample_dt * 1e-9):
        times = np.append(times, total)
    else:
        times[-1] = total
    cumulative = np.cumsum(durations)
    positions = np.zeros((len(times), 3), dtype=np.float64)
    velocities = np.zeros_like(positions)
    accelerations = np.zeros_like(positions)
    segment_ids = np.zeros(len(times), dtype=np.int64)
    local_times = np.zeros(len(times), dtype=np.float64)
    normalized_times = np.zeros(len(times), dtype=np.float64)
    for row, global_time in enumerate(times):
        segment = int(np.searchsorted(cumulative, global_time, side="left"))
        segment = min(segment, len(durations) - 1)
        segment_start = float(cumulative[segment] - durations[segment])
        local = min(max(float(global_time - segment_start), 0.0), float(durations[segment]))
        u = local / float(durations[segment])
        segment_ids[row] = segment
        local_times[row] = local
        normalized_times[row] = u
        for axis_index, axis in enumerate(("x", "y", "z")):
            coefficients = _axis_coefficients(msg, segment, axis)
            positions[row, axis_index] = _evaluate(coefficients, u, 0, float(durations[segment]))
            velocities[row, axis_index] = _evaluate(coefficients, u, 1, float(durations[segment]))
            accelerations[row, axis_index] = _evaluate(coefficients, u, 2, float(durations[segment]))
    return {
        "time": times,
        "segment_id": segment_ids,
        "segment_local_time": local_times,
        "u": normalized_times,
        "position": positions,
        "velocity": velocities,
        "acceleration": accelerations,
    }


def write_csv(path: Path, sampled: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ["time", "segment_id", "segment_local_time", "u"]
    header += [f"position_{axis}" for axis in "xyz"]
    header += [f"velocity_{axis}" for axis in "xyz"]
    header += [f"acceleration_{axis}" for axis in "xyz"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for index in range(len(sampled["time"])):
            row = [
                sampled["time"][index],
                sampled["segment_id"][index],
                sampled["segment_local_time"][index],
                sampled["u"][index],
            ]
            row += sampled["position"][index].tolist()
            row += sampled["velocity"][index].tolist()
            row += sampled["acceleration"][index].tolist()
            writer.writerow(row)


def csv_matrix(path: Path) -> np.ndarray:
    return np.loadtxt(path, delimiter=",", skiprows=1, dtype=np.float64)
