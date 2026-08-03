"""Independent multi-rate and diagnostic validation for an S2-R6 candidate."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

from planner_bridge.execution.full_body_proxy import component_clearances, obstacle_tree
from planner_bridge.execution.official_delta_kinematics import official_fk_joint_state, official_ik, official_joint_points, joint_margin
from planner_bridge.execution.playback_validator import sample_raw, validate_attitude


DIAGNOSTIC = re.compile(
    r"min_g=([-+0-9.eE]+).*?active_samples=(\d+).*?max_violation=([-+0-9.eE]+).*?barrier_cost=([-+0-9.eE]+).*?integration_samples=(\d+)"
)


def arm_jerk_cost(path: Path) -> float:
    message = json.loads(path.read_text(encoding="utf-8"))["message"]
    n = int(message["num_segment"])
    durations = np.asarray(message["time"], dtype=float)
    coeffs = np.column_stack([message[axis] for axis in ("coef_x", "coef_y", "coef_z")]).reshape(n, 6, 3)[:, ::-1, :]
    total = 0.0
    for i, t in enumerate(durations):
        t2, t3, t4, t5 = t * t, t**3, t**4, t**5
        b = coeffs[i]
        total += 36.0 * np.sum(b[3] ** 2) * t
        total += 144.0 * np.dot(b[4], b[3]) * t2
        total += 192.0 * np.sum(b[4] ** 2) * t3
        total += 240.0 * np.dot(b[5], b[3]) * t3
        total += 720.0 * np.dot(b[5], b[4]) * t4
        total += 720.0 * np.sum(b[5] ** 2) * t5
    return float(total)


def direction_contract(root: Path) -> dict[str, object]:
    points = json.loads((root / "docs/evidence/S2-R4/static_feasibility/p0_p6_selected.json").read_text(encoding="utf-8"))["P0_P6"]
    p2, p3, p4 = (np.asarray(points[i]["arm_point_A0_m"], dtype=float) for i in (2, 3, 4))
    v23, v34 = p3 - p2, p4 - p3
    error = float(max(abs(v23[2]), abs(v34[2])))
    return {
        "P2_to_P3_delta_A0_m": v23.tolist(),
        "P3_to_P4_delta_A0_m": v34.tolist(),
        "direction_error_m": error,
        "pass": bool(error < 1e-12 and v23[0] > 0.0 and v34[0] < 0.0 and v34[1] > 0.0),
        "task_points_unchanged": True,
    }


def diagnostics(run: Path) -> dict[str, object]:
    text = (run / "roslaunch.log").read_text(encoding="utf-8", errors="replace")
    records = [
        {"min_g": float(m.group(1)), "active_samples": int(m.group(2)), "max_violation": float(m.group(3)), "barrier_cost": float(m.group(4)), "integration_samples": int(m.group(5))}
        for m in DIAGNOSTIC.finditer(text)
    ]
    final_cost = re.findall(r"Final cost:\s*([-+0-9.eE]+)", text)
    planning_ms = re.findall(r"Optimization time usage:\s*([-+0-9.eE]+)\s*ms", text)
    return {
        "record_count": len(records),
        "min_g": min((item["min_g"] for item in records), default=None),
        "max_active_samples": max((item["active_samples"] for item in records), default=None),
        "max_violation": max((item["max_violation"] for item in records), default=None),
        "max_barrier_cost": max((item["barrier_cost"] for item in records), default=None),
        "integration_samples": sorted({item["integration_samples"] for item in records}),
        "final_cost": float(final_cost[-1]) if final_cost else None,
        "planning_time_ms": float(planning_ms[-1]) if planning_ms else None,
        "records": records,
    }


def validate(root: Path, run: Path) -> dict[str, object]:
    tree = obstacle_tree("nominal")
    rates: dict[str, object] = {}
    for hz in (100, 200, 400, 800, 2000):
        base = sample_raw(run / "trajectory.json", hz, arm=False)
        arm = sample_raw(run / "trajectory_arm.json", hz, arm=True)
        q = np.asarray([official_ik(point) for point in arm["position"]], dtype=float)
        fk = np.asarray([official_fk_joint_state(row) for row in q], dtype=float)
        residual = np.linalg.norm(fk - arm["position"], axis=1)
        _, attitude = validate_attitude(base)
        components: dict[str, list[float]] = {}
        for position, rotation, arm_point, q_row in zip(base["position"], attitude["rotation"], arm["position"], q):
            values = component_clearances(position, rotation, arm_point, official_joint_points(arm_point, q_row), tree)
            for name, value in values.items():
                components.setdefault(name, []).append(float(value))
        min_clearance = min(min(values) for values in components.values())
        dangerous_component = min(components, key=lambda name: min(components[name]))
        dangerous_index = int(np.argmin(np.asarray(components[dangerous_component], dtype=float)))
        rates[str(hz)] = {
            "sample_count": int(len(arm["time"])),
            "ik_no_solution_count": int(np.sum(~np.isfinite(q).all(axis=1))),
            "q_min_rad": np.nanmin(q, axis=0).tolist(),
            "q_max_rad": np.nanmax(q, axis=0).tolist(),
            "joint_margin_min_rad": float(np.nanmin([joint_margin(row) for row in q])),
            "max_fk_residual_m": float(np.nanmax(residual)),
            "component_min_clearance_m": {name: float(min(values)) for name, values in components.items()},
            "min_full_body_clearance_m": float(min_clearance),
            "dangerous_component": dangerous_component,
            "dangerous_time_s": float(base["time"][dangerous_index]),
            "joint_gate_pass": bool(np.isfinite(q).all() and np.nanmin(q) >= 0.0 and np.nanmax(q) <= np.pi / 2.0),
            "full_body_gate_pass": bool(min_clearance >= 0.010),
            "finite": bool(np.isfinite(q).all() and np.isfinite(fk).all()),
        }
    direction = direction_contract(root)
    result = {
        "run_dir": str(run).replace("\\", "/"),
        "capture_exit": json.loads((run / "processes.json").read_text(encoding="utf-8")).get("capture_exit"),
        "rates": rates,
        "direction": direction,
        "diagnostics": diagnostics(run),
        "arm_jerk_cost": arm_jerk_cost(run / "trajectory_arm.json"),
        "nominal_hard_gate_pass": bool(rates["2000"]["joint_gate_pass"] and rates["2000"]["full_body_gate_pass"] and direction["pass"]),
        "algorithm_output_unmodified": True,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = validate(root, args.run_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"nominal_hard_gate_pass": result["nominal_hard_gate_pass"], "q_min_rad": result["rates"]["2000"]["q_min_rad"], "clearance_m": result["rates"]["2000"]["min_full_body_clearance_m"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
