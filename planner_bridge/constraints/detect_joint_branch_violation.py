"""Detect official Delta joint-branch violations in a captured Cartesian arm path."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from planner_bridge.execution.official_delta_kinematics import joint_margin, official_ik
from planner_bridge.execution.playback_validator import evaluate_message
from planner_bridge.export.sampling import load_captured_message


def _event(index: int, times: np.ndarray, base: dict[str, np.ndarray], arm: dict[str, np.ndarray], q: np.ndarray,
           durations: np.ndarray) -> dict[str, Any]:
    t = float(times[index])
    cumulative = np.cumsum(durations)
    segment = min(int(np.searchsorted(cumulative, t, side="left")), len(durations) - 1)
    segment_start = float(cumulative[segment] - durations[segment])
    local = min(max(t - segment_start, 0.0), float(durations[segment]))
    values = {
        "time_s": t,
        "segment_id": segment,
        "segment_local_time_s": float(local),
        "segment_local_normalized_time": float(local / durations[segment]),
        "base_position_WB_m": base["position"][index].tolist(),
        "base_velocity_WB_m_s": base["velocity"][index].tolist(),
        "base_acceleration_WB_m_s2": base["acceleration"][index].tolist(),
        "arm_cartesian_position_A0_m": arm["position"][index].tolist(),
        "arm_cartesian_velocity_A0_m_s": arm["velocity"][index].tolist(),
        "arm_cartesian_acceleration_A0_m_s2": arm["acceleration"][index].tolist(),
        "q_rad": q[index].tolist(),
        "joint_margin_rad": float(joint_margin(q[index])),
    }
    return values


def detect_violations(arm_path: Path, base_path: Path, sample_hz: int = 2000,
                      adaptive_dt_s: float = 0.0005) -> dict[str, Any]:
    """Return interval and event records without clipping or projecting output."""
    arm_msg = load_captured_message(arm_path)["message"]
    base_msg = load_captured_message(base_path)["message"]
    total = float(np.sum(np.asarray(arm_msg["time"], dtype=float)))
    dt = min(float(adaptive_dt_s), 1.0 / float(sample_hz))
    times = np.arange(0.0, total + 0.5 * dt, dt, dtype=float)
    times = times[times <= total + 1e-10]
    arm = evaluate_message(arm_msg, times, arm=True)
    base = evaluate_message(base_msg, times, arm=False)
    q = np.asarray([official_ik(point) for point in arm["position"]], dtype=float)
    lower = q < 0.0
    upper = q > math.pi / 2.0
    invalid = np.any(lower | upper, axis=1)
    padded = np.r_[False, invalid, False].astype(np.int8)
    starts = np.flatnonzero(np.diff(padded) == 1)
    ends = np.flatnonzero(np.diff(padded) == -1) - 1
    durations = np.asarray(arm_msg["time"], dtype=float)
    intervals: list[dict[str, Any]] = []
    for start, end in zip(starts, ends):
        local_q = q[start : end + 1]
        local_margin = np.asarray([joint_margin(row) for row in local_q])
        minimum = int(start + np.argmin(local_margin))
        offending = np.flatnonzero(np.any((q[start : end + 1] < 0.0) | (q[start : end + 1] > math.pi / 2.0), axis=0)).tolist()
        row: dict[str, Any] = {
            "entry_time_s": float(times[start]),
            "minimum_time_s": float(times[minimum]),
            "exit_time_s": float(times[end]),
            "duration_s": float(times[end] - times[start]),
            "offending_joints": [f"q{i + 1}" for i in offending],
            "entry": _event(int(start), times, base, arm, q, durations),
            "minimum": _event(minimum, times, base, arm, q, durations),
            "exit": _event(int(end), times, base, arm, q, durations),
        }
        if row["duration_s"] > 0.25:
            q25 = int(start + round(0.25 * (end - start)))
            q75 = int(start + round(0.75 * (end - start)))
            row["quartiles"] = {"q25": _event(q25, times, base, arm, q, durations), "q75": _event(q75, times, base, arm, q, durations)}
        intervals.append(row)
    return {
        "source_arm": str(arm_path).replace("\\", "/"),
        "source_base": str(base_path).replace("\\", "/"),
        "sample_hz": int(round(1.0 / dt)),
        "adaptive_dt_s": dt,
        "sample_count": int(len(times)),
        "official_joint_contract_rad": [0.0, math.pi / 2.0],
        "ik_no_solution_count": int(np.sum(~np.isfinite(q).all(axis=1))),
        "q_min_rad": np.nanmin(q, axis=0).tolist(),
        "q_max_rad": np.nanmax(q, axis=0).tolist(),
        "min_joint_margin_rad": float(np.nanmin([joint_margin(row) for row in q])),
        "violating_intervals": intervals,
        "joint_gate_pass": bool(np.isfinite(q).all() and not invalid.any()),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-hz", type=int, default=2000)
    args = parser.parse_args()
    result = detect_violations(args.arm, args.base, sample_hz=args.sample_hz)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"intervals": len(result["violating_intervals"]), "q_min": result["q_min_rad"], "joint_gate_pass": result["joint_gate_pass"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
