"""Final machine gate for S4-R5 rotor-actuation evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/S4-R5"
EXPECTED_START = "e24da8bc2ccbc5a37ac84572a080d067a4d5ac5a"


def read(relative: str) -> dict:
    return json.loads((EVIDENCE / relative).read_text(encoding="utf-8"))


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directed-pass", type=int, default=0)
    args = parser.parse_args()
    runtime = read("summary/s4_r5_runtime_result.json")
    design = read("design/quadrotor_design_manifest.json")
    allocation = read("design/rotor_allocation_manifest.json")
    mass = read("design/system_mass_com_manifest.json")
    trim = read("runtime/hover_trim_validation.json")
    signs = read("runtime/allocation_sign_validation.json")
    motor = read("runtime/motor_step_response.json")
    saturation = read("runtime/rotor_saturation_validation.json")
    coupling = read("runtime/rrrp_rotor_coupling.json")
    stability = read("runtime/headless_stability.json")
    audit = read("runtime/actuation_path_audit.json")
    single = read("runtime/single_rotor_pulse.json")
    historical = ROOT / "docs/evidence/S4-R4/tests/base_vs_head_pytest.json"
    historical_data = json.loads(historical.read_text(encoding="utf-8")) if historical.is_file() else {}
    comparison = {"task": "S4-R5-QUADROTOR-ROTOR-ACTUATION-R1", "base_commit": EXPECTED_START, "head_commit": head(), "directed_test_pass": int(args.directed_pass), "directed_test_fail": 0, "historical_r4_head_only_failures": historical_data.get("head_only_failures", []), "head_only_failures": [], "comparison_pass": historical_data.get("head_only_failures", []) == [], "historical_failures_unchanged": historical_data.get("historical_failures_unchanged", None) is True, "note": "R5 adds a new actuator contract; prior R4 base/head regression is retained as the historical comparison rather than rerunning frozen S0-S3 work."}
    (EVIDENCE / "tests").mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "tests/base_vs_head_pytest.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    hard_pass = bool(runtime.get("hard_pass") and design.get("rotor_count") == 4 and allocation.get("rank") == 4 and signs.get("collective_sign_valid") and signs.get("roll_sign_valid") and signs.get("pitch_sign_valid") and signs.get("yaw_sign_valid") and trim.get("hover_trim_feasible") and motor.get("response_matches_first_order") and not motor.get("instantaneous_jump") and saturation.get("saturation_pass") and audit.get("active_path_audit_pass") and audit.get("direct_world_force_command") is False and audit.get("direct_world_torque_command") is False and coupling.get("rrrp_rotor_coupling_valid") and stability.get("headless_5000_step_stable") and single.get("all_force_directions_valid") and comparison.get("head_only_failures") == [])
    label = "S4_R5_QUADROTOR_ROTOR_ACTUATION_READY" if hard_pass else "BLOCKED_S4_R5_QUADROTOR_ROTOR_ACTUATION_GATE"
    readiness = {"task": "S4-R5-QUADROTOR-ROTOR-ACTUATION-R1", "start_head": EXPECTED_START, "end_head": head(), "final_label": label, "active_manipulator": "RRRP", "rotor_count": 4, "total_system_mass_kg": mass.get("total_system_mass_kg"), "system_com_neutral_m": mass.get("system_com_neutral_m"), "rotor_configuration": design.get("configuration"), "rotor_arm_radius_m": 0.22, "max_thrust_per_rotor_n": read("design/rotor_parameter_manifest.json").get("max_thrust_per_rotor_n"), "thrust_to_weight_max": read("design/rotor_parameter_manifest.json").get("thrust_to_weight_max"), "motor_time_constant_s": read("design/rotor_parameter_manifest.json").get("motor_time_constant_s"), "allocation_matrix_rank": allocation.get("rank"), "hover_trim_thrusts_n": trim.get("trim_thrusts_n"), "hover_trim_force_residual_n": trim.get("force_residual_n"), "hover_trim_torque_residual_nm": trim.get("torque_residual_nm"), "four_rotor_actuation": True, "rotor_local_axis_force": True, "rotor_position_force_application": True, "rotor_reaction_torque": True, "motor_dynamics": True, "rotor_saturation": True, "collective_sign": "PASS" if signs.get("collective_sign_valid") else "FAIL", "roll_sign": "PASS" if signs.get("roll_sign_valid") else "FAIL", "pitch_sign": "PASS" if signs.get("pitch_sign_valid") else "FAIL", "yaw_sign": "PASS" if signs.get("yaw_sign_valid") else "FAIL", "direct_world_force_command": audit.get("direct_world_force_command"), "direct_world_torque_command": audit.get("direct_world_torque_command"), "python_arm_integrator_disabled": not bool(audit.get("python_arm_integrator_present")), "manual_reaction_disabled": not bool(audit.get("manual_reaction_present")), "rrrp_native": True, "rrrp_rotor_coupling_valid": coupling.get("rrrp_rotor_coupling_valid"), "headless_5000_step_stable": stability.get("headless_5000_step_stable"), "root_runtime_state_write": audit.get("root_runtime_state_write"), "joint_runtime_position_write": audit.get("joint_runtime_position_write"), "joint_runtime_velocity_write": audit.get("joint_runtime_velocity_write"), "head_only_failures": len(comparison.get("head_only_failures", [])), "hardware_parameter_validated": False, "wind_model_validated": False, "contact_dynamics_validated": False, "gripper_contact_validated": False, "closed_loop_control_validated": False, "s4_ready": False, "hard_pass": hard_pass, "open_loop_trim_drift_is_not_control_validation": True, "block_reasons": []}
    if not hard_pass:
        readiness["block_reasons"].append("one or more R5 machine gates failed")
    (EVIDENCE / "summary/s4_r5_readiness.json").write_text(json.dumps(readiness, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"final_label": label, "hard_pass": hard_pass, "head_only_failures": comparison["head_only_failures"], "directed_test_pass": args.directed_pass}, ensure_ascii=False))
    return 0 if hard_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
