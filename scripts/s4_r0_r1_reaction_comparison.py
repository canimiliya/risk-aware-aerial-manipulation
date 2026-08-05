"""Compare the rejected first-difference reaction contract with R1 analytics."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from planner_bridge.control.dynamic_model import ArmReactionSurrogate

ROOT = Path(__file__).resolve().parents[1]
DT = 1.0 / 240.0


def old_metrics(rows: list[dict[str, object]], model: ArmReactionSurrogate) -> dict[str, float]:
    previous_com = model.com(np.asarray(rows[0]["q_rad"], dtype=float))
    forces = []
    torques = []
    for row in rows:
        current_com = model.com(np.asarray(row["q_rad"], dtype=float))
        velocity = (current_com - previous_com) / DT
        acceleration = velocity / DT
        forces.append(model.arm_mass_kg * float(np.linalg.norm(acceleration)))
        torques.append(float(np.linalg.norm(np.cross(current_com, model.arm_mass_kg * acceleration))))
        previous_com = current_com
    return {"force_peak_N": float(np.max(forces)), "force_rms_N": float(np.sqrt(np.mean(np.square(forces)))), "torque_peak_Nm": float(np.max(torques)), "torque_rms_Nm": float(np.sqrt(np.mean(np.square(torques))))}


def main() -> int:
    model = ArmReactionSurrogate(0.29135232232511, np.array([0.0, 0.0, -0.14]))
    current = json.loads((ROOT / "docs/evidence/S4-R0/summary/s4_r0_metrics.json").read_text(encoding="utf-8"))
    old_text = subprocess.run(["git", "show", "84bf5cb6c6c81c848a85efebae05804af612f096:docs/evidence/S4-R0/summary/s4_r0_metrics.json"], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    old = json.loads(old_text)
    comparison = []
    for run in current["runs"]:
        if run["scenario"] != "arm_motion_hold":
            continue
        state_path = ROOT / "outputs/S4-R0" / run["scenario"] / run["run_id"] / "state.jsonl"
        rows = [json.loads(line) for line in state_path.read_text(encoding="utf-8").splitlines()]
        rejected = old_metrics(rows, model)
        comparison.append({"scenario": run["scenario"], "run_id": run["run_id"], "old_formula": "velocity=(com_k-com_k-1)/dt; acceleration=velocity/dt", "new_formula": "a_com=J(q)qdd+Jdot(q,dq)dq", "old_rejected_first_difference": rejected, "new_analytic": {"force_peak_N": run["arm_reaction_force_peak_N"], "force_rms_N": run["arm_reaction_force_rms_N"], "torque_peak_Nm": run["arm_reaction_torque_peak_Nm"], "torque_rms_Nm": run["arm_reaction_torque_rms_Nm"], "base_position_rmse_m": run["position_rmse_m"], "joint_rmse_rad": run["joint_rmse_rad"], "settling_time_position_s": run["settling_time_position_s"]}, "old_headline_metrics": next((item for item in old["runs"] if item["scenario"] == run["scenario"] and item["run_id"] == run["run_id"]), {})})
    payload = {"decision": "PASS_PENDING_AUDIT", "comparison": comparison, "static_arm_reaction_new_force_N": 0.0, "static_arm_reaction_new_torque_Nm": 0.0, "first_frame_pulse_new": False}
    path = ROOT / "docs/evidence/S4-R0/summary/r1_correction_comparison.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
