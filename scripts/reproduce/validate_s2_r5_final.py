"""Final multi-rate IK/FK convergence check for the last S2-R5 nominal run."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from planner_bridge.execution.official_delta_kinematics import official_fk_joint_state, official_ik, joint_margin
from planner_bridge.execution.playback_validator import sample_raw


RUN = ROOT / "docs/evidence/S2-R5/runtime/round_3_nominal"
OUT = ROOT / "docs/evidence/S2-R5/final_validation/frequency_convergence.json"


def main() -> int:
    results = {}
    for hz in (100, 200, 400, 800, 2000):
        arm = sample_raw(RUN / "trajectory_arm.json", hz, arm=True)
        q = np.asarray([official_ik(point) for point in arm["position"]], dtype=float)
        fk = np.asarray([official_fk_joint_state(row) for row in q], dtype=float)
        residual = np.linalg.norm(fk - arm["position"], axis=1)
        qdot = np.gradient(q, arm["time"], axis=0, edge_order=2)
        qddot = np.gradient(qdot, arm["time"], axis=0, edge_order=2)
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
            "finite": bool(np.isfinite(q).all() and np.isfinite(fk).all() and np.isfinite(qdot).all() and np.isfinite(qddot).all()),
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"run": str(RUN).replace("\\", "/"), "adaptive_dt_s": 0.0005, "rates": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: {"q2_min_rad": v["q_min_rad"][1], "max_fk_residual_m": v["max_fk_residual_m"]} for k, v in results.items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
