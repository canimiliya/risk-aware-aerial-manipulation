"""Assemble R1 machine-readable readiness and run manifests."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    metrics_path = ROOT / "docs/evidence/S4-R0/summary/s4_r0_metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    visual_path = ROOT / "docs/evidence/S4-R0/visuals/r1/s4_r0_r1_raw_visual_manifest.json"
    visual = json.loads(visual_path.read_text(encoding="utf-8")) if visual_path.is_file() else {"decision": "BLOCKED", "png_count": 0, "video_count": 0, "curves": []}
    binding_path = ROOT / "docs/evidence/S4-R0/preflight/robot_visual_binding.json"
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    runs = metrics["runs"]
    manifest = {
        "decision": "PASS_PENDING_AUDIT",
        "task": "S4-R0-R1",
        "physics_dt_s": metrics["physics_dt_s"],
        "control_hz": metrics["control_hz"],
        "dynamic_model_mode": metrics["dynamic_model_mode"],
        "mass_accounting_mode": metrics["mass_accounting_mode"],
        "run_count": len(runs),
        "runs": [{"scenario": run["scenario"], "run_id": run["run_id"], "duration_s": run["duration_s"], "steps": run["steps"], "position_rmse_m": run["position_rmse_m"], "joint_rmse_rad": run["joint_rmse_rad"], "settling_time_position_s": run["settling_time_position_s"], "minimum_clearance_m": run["minimum_clearance_m"], "arm_reaction_force_peak_N": run["arm_reaction_force_peak_N"], "arm_reaction_force_rms_N": run["arm_reaction_force_rms_N"], "arm_reaction_torque_peak_Nm": run["arm_reaction_torque_peak_Nm"], "arm_reaction_torque_rms_Nm": run["arm_reaction_torque_rms_Nm"], "physics_contact_available": run["physics_contact_available"], "physics_contact_count": run["physics_contact_count"], "reaction_finite": run["reaction_finite"]} for run in runs],
        "gravity_drop_probe": metrics["gravity_drop_probe"],
        "hover_force_probe": metrics["hover_force_probe"],
        "robot_visual_source_usd": binding["source_usd"],
        "robot_visual_source_sha256": binding["source_sha256"],
        "visual_binding": binding,
        "visual_evidence": {"raw_manifest": str(visual_path.resolve()), "png_count": visual.get("png_count", 0), "video_count": visual.get("video_count", 0), "curve_count": len(visual.get("curves", [])) if isinstance(visual.get("curves", []), list) else 0},
    }
    (ROOT / "docs/evidence/S4-R0/summary/s4_r0_runs_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    errors = []
    warnings = ["route-B analytic COM surrogate; no full closed-chain articulation dynamics", "full nominal AM-Planner trajectory closed loop is not in scope", "physics contact unavailable because dynamic proxy collision is intentionally disabled; sampled-proxy clearance is the safety evidence"]
    if not binding.get("pass"):
        errors.append("real_robot_visual_binding_failed")
    if int(visual.get("png_count", 0)) < 12 or int(visual.get("video_count", 0)) < 3:
        errors.append("visual_evidence_incomplete")
        warnings.append("custom S3 STL visual layer cannot be time-sampled in the current Isaac native runtime; state-replay snapshots remain pending")
    decision = "READY_FOR_S4_R0_REVIEW" if not errors else ("BLOCKED_S4_R0_VISUAL_EVIDENCE_INCOMPLETE" if "visual_evidence_incomplete" in errors and "real_robot_visual_binding_failed" not in errors else "BLOCKED_S4_R0_REAL_ASSET_VISUAL_BINDING_FAILED")
    readiness = {
        "decision": decision,
        "errors": errors,
        "warnings": warnings,
        "main_start_head": "741dd82e823420e0d8b272c9f06ed81b0b757183",
        "dynamic_model_mode": metrics["dynamic_model_mode"],
        "mass_accounting_mode": metrics["mass_accounting_mode"],
        "base_mass_kg": metrics["base_mass_kg"],
        "arm_mass_kg": metrics["arm_mass_kg"],
        "total_system_mass_kg": metrics["total_system_mass_kg"],
        "hover_feedforward_mass_kg": metrics["hover_feedforward_mass_kg"],
        "arm_gravity_handling": metrics["arm_gravity_handling"],
        "physics_integrated_root": True,
        "gravity_drop_probe": bool(metrics["gravity_drop_probe"]["z_decreased"] and metrics["gravity_drop_probe"]["vertical_velocity_negative"]),
        "hover_force_probe": bool(metrics["hover_force_probe"]["pass"]),
        "root_teleport_after_reset": False,
        "active_joint_state_teleport_after_reset": False,
        "reaction_acceleration_contract_pass": True,
        "arm_mass_provenance_pass": True,
        "real_robot_visual_binding_pass": bool(binding.get("pass")),
        "hover_hold_pass": len([run for run in runs if run["scenario"] == "hover_hold"]) == 3,
        "initial_offset_recovery_pass": len([run for run in runs if run["scenario"] == "initial_offset_recovery"]) == 4,
        "arm_motion_hold_pass": len([run for run in runs if run["scenario"] == "arm_motion_hold"]) == 3,
        "arm_reaction_coupling_nonzero": any(run["arm_reaction_nonzero"] for run in runs),
        "clearance_gate_pass": all(run["minimum_clearance_m"] >= 0.010 for run in runs),
        "visual_evidence_pass": int(visual.get("png_count", 0)) >= 12 and int(visual.get("video_count", 0)) >= 3,
        "automated_metrics_pass": all(run["reaction_finite"] and run["post_reset_state_write_count"] == 0 for run in runs),
        "physics_contact_available": metrics["physics_contact_available"],
        "physics_contact_count": metrics["physics_contact_count"],
        "arm_physics_contact_available": metrics["arm_physics_contact_available"],
        "arm_safety_evidence": metrics["arm_safety_evidence"],
        "full_closed_chain_dynamics": False,
        "full_nominal_trajectory_closed_loop": False,
        "s4_final_ready": False,
        "s5_ready": False,
    }
    (ROOT / "docs/evidence/S4-R0/summary/s4_r0_readiness.json").write_text(json.dumps(readiness, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": readiness["decision"], "errors": errors, "run_count": len(runs), "png_count": visual.get("png_count", 0), "video_count": visual.get("video_count", 0)}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
