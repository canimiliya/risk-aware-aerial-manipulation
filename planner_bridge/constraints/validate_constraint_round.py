"""Independent round validator for S2-R5 task-level constraints."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from planner_bridge.execution.full_body_proxy import component_clearances, obstacle_tree
from planner_bridge.execution.official_delta_kinematics import official_fk_joint_state, official_ik, official_joint_points, joint_margin
from planner_bridge.execution.official_flatness_wrapper import quaternion_to_rotation_wxyz
from planner_bridge.execution.playback_validator import evaluate_message, validate_attitude
from planner_bridge.export.sampling import load_captured_message

from .detect_joint_branch_violation import detect_violations


def validate_round(run_dir: Path, constraints_path: Path, variant: str = "nominal", sample_hz: int = 2000) -> dict[str, Any]:
    arm_path = run_dir / "trajectory_arm.json"
    base_path = run_dir / "trajectory.json"
    violation = detect_violations(arm_path, base_path, sample_hz=sample_hz)
    arm_msg = load_captured_message(arm_path)["message"]
    base_msg = load_captured_message(base_path)["message"]
    total = float(np.sum(np.asarray(arm_msg["time"], dtype=float)))
    times = np.arange(0.0, total + 0.5 / sample_hz, 1.0 / sample_hz)
    times = times[times <= total + 1e-10]
    arm = evaluate_message(arm_msg, times, arm=True)
    base = evaluate_message(base_msg, times, arm=False)
    q = np.asarray([official_ik(point) for point in arm["position"]])
    fk_residuals = np.asarray([np.linalg.norm(official_fk_joint_state(q_row) - point) for q_row, point in zip(q, arm["position"])])
    qdot = np.gradient(q, times, axis=0, edge_order=2)
    qddot = np.gradient(qdot, times, axis=0, edge_order=2)
    _, attitude = validate_attitude({**base, "time": times, "yaw": np.zeros(len(times)), "yaw_dot": np.full(len(times), 0.01)})
    clearances: list[float] = []
    component_values: dict[str, list[float]] = {}
    tree = obstacle_tree(variant)
    for position, rotation, arm_point, q_row in zip(base["position"], attitude["rotation"], arm["position"], q):
        values = component_clearances(position, rotation, arm_point, official_joint_points(arm_point, q_row), tree)
        clearances.append(min(values.values()))
        for name, value in values.items():
            component_values.setdefault(name, []).append(float(value))
    constraints = json.loads(constraints_path.read_text(encoding="utf-8"))
    fixed = constraints.get("new_mode3", [])
    fixed_margins = [float(item["target_joint_margin_rad"]) for item in fixed]
    fixed_points = np.asarray([item["arm_point_A0_m"] for item in fixed], dtype=float) if fixed else np.empty((0, 3))
    distances = np.linalg.norm(arm["position"][:, None, :] - fixed_points[None, :, :], axis=2) if len(fixed_points) else np.empty((len(times), 0))
    nearest = np.min(distances, axis=1) if distances.size else np.full(len(times), np.nan)
    curvature = np.linalg.norm(np.gradient(np.gradient(arm["position"], times, axis=0, edge_order=2), times, axis=0, edge_order=2), axis=1)
    return {
        "run_dir": str(run_dir).replace("\\", "/"),
        "sample_hz": sample_hz,
        "sample_count": int(len(times)),
        "fixed_mode3_count": len(fixed),
        "fixed_point_joint_margin_rad": fixed_margins,
        "fixed_point_hard_pass": bool(all(value >= 0.0 for value in fixed_margins)),
        "fixed_point_preferred_pass": bool(all(value >= 0.02 for value in fixed_margins)),
        "fixed_point_robust_pass": bool(all(value >= 0.05 for value in fixed_margins)),
        "q_min_rad": np.min(q, axis=0).tolist(),
        "q_max_rad": np.max(q, axis=0).tolist(),
        "q2_min_rad": float(np.min(q[:, 1])),
        "joint_margin_min_rad": float(np.min([joint_margin(row) for row in q])),
        "qdot_max_rad_s": float(np.max(np.abs(qdot))),
        "qddot_max_rad_s2": float(np.max(np.abs(qddot))),
        "ik_no_solution_count": int(np.sum(~np.isfinite(q).all(axis=1))),
        "max_fk_residual_m": float(np.max(fk_residuals)),
        "min_full_body_clearance_m": float(np.min(clearances)),
        "full_body_gate_pass": bool(np.min(clearances) >= 0.010),
        "component_min_clearance_m": {name: float(np.min(values)) for name, values in component_values.items()},
        "dangerous_component": min(component_values, key=lambda name: min(component_values[name])),
        "arm_polynomial_max_curvature_m_s2": float(np.max(curvature)),
        "new_violation_intervals": violation["violating_intervals"],
        "nearest_new_fixed_point_time_s": float(times[int(np.nanargmin(nearest))]) if np.isfinite(nearest).any() else None,
        "nearest_new_fixed_point_cartesian_distance_m": float(np.nanmin(nearest)) if np.isfinite(nearest).any() else None,
        "joint_gate_pass": bool(violation["joint_gate_pass"]),
        "projection_is_not_output_trajectory": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--constraints", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-hz", type=int, default=2000)
    args = parser.parse_args()
    result = validate_round(args.run_dir, args.constraints, sample_hz=args.sample_hz)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"q2_min_rad": result["q2_min_rad"], "joint_gate_pass": result["joint_gate_pass"], "full_body_gate_pass": result["full_body_gate_pass"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
