"""Finalize machine-readable S4-R3 evidence after an asset-topology blocker."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


BLOCKER = "BLOCKED_S4_R3_DELTA_TOPOLOGY_UNRESOLVED"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    repo = args.repo.resolve()
    asset_root = repo / "docs/evidence/S4-R3/asset"
    runtime_root = repo / "docs/evidence/S4-R3/runtime"
    summary_root = repo / "docs/evidence/S4-R3/summary"
    topology = json.loads((asset_root / "delta_topology_manifest.json").read_text(encoding="utf-8"))
    asset = json.loads((asset_root / "native_asset_manifest.json").read_text(encoding="utf-8"))
    reason = topology["blocker"]

    write_json(runtime_root / "native_runtime_manifest.json", {
        "task": "S4-R3-NATIVE-MULTIBODY-SKELETON-R1",
        "status": "NOT_RUN_ASSET_BLOCKER",
        "final_label": BLOCKER,
        "render": False,
        "native_multibody_mode": False,
        "native_execution_started": False,
        "headless_1000_step_stable": False,
        "native_exit": None,
        "physics_explosion": None,
        "nan_count": None,
        "inf_count": None,
        "root_states_recorded": False,
        "link_states_recorded": False,
        "joint_states_recorded": False,
        "reason": reason,
    })
    write_json(runtime_root / "loop_closure_metrics.json", {
        "task": "S4-R3-NATIVE-MULTIBODY-SKELETON-R1",
        "status": "NOT_RUN_ASSET_BLOCKER",
        "final_label": BLOCKER,
        "position": {"mean_m": None, "rms_m": None, "max_m": None, "p95_m": None},
        "orientation": {"mean_deg": None, "rms_deg": None, "max_deg": None, "p95_deg": None},
        "skeleton_thresholds": {"max_position_m_lt": 0.001, "max_orientation_deg_lt": 1.0},
        "high_fidelity_targets": {"position_m_lt": 0.0001, "orientation_deg_lt": 0.1},
        "pass": False,
        "reason": reason,
    })
    write_json(runtime_root / "internal_reaction_metrics.json", {
        "task": "S4-R3-NATIVE-MULTIBODY-SKELETON-R1",
        "status": "NOT_RUN_ASSET_BLOCKER",
        "final_label": BLOCKER,
        "manual_reaction_force_calls": None,
        "manual_reaction_torque_calls": None,
        "manual_arm_gravity_calls": None,
        "base_dynamic_response_present": None,
        "native_solver_generated_coupling": False,
        "reason": reason,
    })
    write_json(runtime_root / "momentum_diagnostics.json", {
        "task": "S4-R3-NATIVE-MULTIBODY-SKELETON-R1",
        "status": "NOT_RUN_ASSET_BLOCKER",
        "final_label": BLOCKER,
        "gravity": False,
        "external_force": False,
        "external_torque": False,
        "linear_momentum_initial": None,
        "linear_momentum_final": None,
        "linear_momentum_max_drift": None,
        "linear_momentum_relative_drift_threshold": 0.01,
        "angular_momentum_initial": None,
        "angular_momentum_final": None,
        "angular_momentum_max_drift": None,
        "angular_momentum_validation_implemented": False,
        "pass": False,
        "reason": reason,
    })
    write_json(runtime_root / "state_write_audit.json", {
        "task": "S4-R3-NATIVE-MULTIBODY-SKELETON-R1",
        "status": "STATIC_GUARD_ONLY",
        "native_execution_path_present": False,
        "root_state_written_after_reset": False,
        "joint_position_written_during_simulation": False,
        "joint_velocity_written_during_simulation": False,
        "active_joint_effort_targets_used": False,
        "legacy_python_joint_integrator_present": True,
        "legacy_manual_reaction_present": True,
        "legacy_mode_required": True,
        "forbidden_native_runtime_writes": ["set_world_pose", "set_world_transform", "set_root_state", "set_joint_position", "set_joint_state", "teleport", "Usd.TimeCode", "stage.SetTimeCode"],
        "reason": "No native execution path was promoted because the source asset cannot reconstruct the Delta closure.",
    })
    readiness = {
        "task": "S4-R3-NATIVE-MULTIBODY-SKELETON-R1",
        "final_label": BLOCKER,
        "legacy_surrogate_preserved": True,
        "native_multibody_mode_implemented": False,
        "floating_base_articulation": False,
        "real_arm_links_dynamic": False,
        "joint_physics_constraint": False,
        "delta_closed_chain": False,
        "active_joint_effort_control": False,
        "passive_joint_solver_integrated": False,
        "python_arm_state_integrator_disabled_native": False,
        "manual_arm_reaction_disabled_native": False,
        "manual_arm_gravity_disabled_native": False,
        "physx_joint_state_readback": False,
        "headless_1000_step_stable": False,
        "loop_closure_validation": False,
        "internal_reaction_emerges_from_solver": False,
        "linear_momentum_diagnostic": False,
        "full_rotor_actuation": False,
        "motor_dynamics": False,
        "hardware_parameter_validated": False,
        "uav_mass_provenance_validated": False,
        "uav_inertia_provenance_validated": False,
        "provisional_uav_inertial_used": True,
        "contact_dynamics_validated": False,
        "energy_momentum_fully_validated": False,
        "high_fidelity_physics_ready": False,
        "s4_ready": False,
        "source_asset": {
            "uav_base_rigid_body_found": asset["uav_base_rigid_body_found"],
            "arm_positive_mass_link_count": asset["arm_positive_mass_link_count"],
            "active_joint_count_candidate": asset["active_joint_count_candidate"],
            "passive_joint_count_candidate": asset["passive_joint_count_candidate"],
            "existing_loop_joint_count": asset["existing_loop_joint_count"],
            "articulation_root_present": asset["articulation_root_present"],
            "floating_base_articulation_candidate": asset["floating_base_articulation_candidate"],
        },
        "blocker": reason,
    }
    write_json(summary_root / "s4_r3_readiness.json", readiness)
    print(json.dumps({"final_label": BLOCKER, "arm_links": asset["arm_positive_mass_link_count"], "active_joints": asset["active_joint_count_candidate"], "passive_joints": asset["passive_joint_count_candidate"], "existing_loop_joints": asset["existing_loop_joint_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
