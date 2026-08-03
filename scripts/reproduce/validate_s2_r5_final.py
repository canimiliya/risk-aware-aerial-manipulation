"""Final multi-rate IK/FK convergence check for the last S2-R5 nominal run."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from planner_bridge.execution.official_delta_kinematics import official_fk_joint_state, official_ik, official_joint_points, joint_margin
from planner_bridge.execution.full_body_proxy import component_clearances, obstacle_tree
from planner_bridge.execution.playback_validator import sample_raw, validate_attitude


RUN = ROOT / "docs/evidence/S2-R5/runtime/round_3_nominal"
OUT = ROOT / "docs/evidence/S2-R5/final_validation/frequency_convergence.json"


def main() -> int:
    results = {}
    tree = obstacle_tree("nominal")
    for hz in (100, 200, 400, 800, 2000):
        base = sample_raw(RUN / "trajectory.json", hz, arm=False)
        arm = sample_raw(RUN / "trajectory_arm.json", hz, arm=True)
        q = np.asarray([official_ik(point) for point in arm["position"]], dtype=float)
        fk = np.asarray([official_fk_joint_state(row) for row in q], dtype=float)
        residual = np.linalg.norm(fk - arm["position"], axis=1)
        qdot = np.gradient(q, arm["time"], axis=0, edge_order=2)
        qddot = np.gradient(qdot, arm["time"], axis=0, edge_order=2)
        _, attitude = validate_attitude(base)
        component_values = {}
        for position, rotation, arm_point, q_row in zip(base["position"], attitude["rotation"], arm["position"], q):
            values = component_clearances(position, rotation, arm_point, official_joint_points(arm_point, q_row), tree)
            for name, value in values.items():
                component_values.setdefault(name, []).append(float(value))
        results[str(hz)] = {
            "sample_hz": hz,
            "sample_count": int(len(arm["time"])),
            "ik_no_solution_count": int(np.sum(~np.isfinite(q).all(axis=1))),
            "q_min_rad": np.nanmin(q, axis=0).tolist(),
            "q_max_rad": np.nanmax(q, axis=0).tolist(),
            "joint_margin_min_rad": float(np.nanmin([joint_margin(row) for row in q])),
            "max_fk_residual_m": float(np.nanmax(residual)),
            "qdot_max_rad_s": float(np.nanmax(np.abs(qdot))),
            "qddot_max_rad_s2": float(np.nanmax(np.abs(qddot))),
            "component_min_clearance_m": {name: float(np.min(values)) for name, values in component_values.items()},
            "min_full_body_clearance_m": float(min(min(values) for values in component_values.values())),
            "full_body_gate_pass": bool(min(min(values) for values in component_values.values()) >= 0.010),
            "dangerous_component": min(component_values, key=lambda name: min(component_values[name])),
            "finite": bool(np.isfinite(q).all() and np.isfinite(fk).all() and np.isfinite(qdot).all() and np.isfinite(qddot).all()),
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"run": str(RUN).replace("\\", "/"), "adaptive_dt_s": 0.0005, "rates": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: {"q2_min_rad": v["q_min_rad"][1], "max_fk_residual_m": v["max_fk_residual_m"]} for k, v in results.items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
