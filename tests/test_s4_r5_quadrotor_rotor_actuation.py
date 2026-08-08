"""Machine contracts for the S4-R5 native rotor actuator evidence."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/S4-R5"


def _read(relative: str) -> dict:
    return json.loads((EVIDENCE / relative).read_text(encoding="utf-8"))


def test_design_and_rrrp_freeze() -> None:
    design = _read("design/quadrotor_design_manifest.json")
    assert design["rotor_count"] == 4
    assert design["configuration"] == "X"
    assert design["active_manipulator"] == "RRRP"
    assert design["rrrp_dof"] == 4
    assert design["rrrp_arm_mass_kg"] == 0.63
    assert design["rrrp_max_reach_m"] == 0.47
    assert design["rrrp_p_stroke_m"] == 0.08
    assert design["provisional"] is True


def test_rotor_parameters_and_geometry_are_explicit() -> None:
    manifest = _read("design/rotor_parameter_manifest.json")
    design = _read("design/quadrotor_design_manifest.json")
    assert manifest["parameter_provenance"] == "ENGINEERING_NOMINAL"
    assert manifest["hardware_parameter_validated"] is False
    assert manifest["provisional"] is True
    assert len(design["rotors"]) == 4
    assert all(len(item["position_body_m"]) == 3 for item in design["rotors"])
    assert all(item["axis_body"] == [0.0, 0.0, 1.0] for item in design["rotors"])


def test_system_mass_com_is_physx_readback() -> None:
    mass = _read("design/system_mass_com_manifest.json")
    assert abs(mass["total_system_mass_kg"] - 1.65) < 1.0e-6
    assert abs(mass["system_com_neutral_m"][0] - 0.09239392992980042) < 1.0e-6
    assert mass["finite"] is True
    assert mass["mass_readback_source"].startswith("PhysX")


def test_allocation_rank_and_derivation() -> None:
    allocation = _read("design/rotor_allocation_manifest.json")
    assert allocation["rank"] == 4
    assert allocation["rank_pass"] is True
    assert allocation["row_order"] == ["Fz", "tau_x", "tau_y", "tau_z"]
    assert "cross(position_body, axis_body)" in allocation["derivation"]


def test_hover_trim_is_feasible() -> None:
    trim = _read("runtime/hover_trim_validation.json")
    assert trim["hover_trim_feasible"] is True
    assert trim["all_nonnegative"] is True
    assert trim["all_below_max"] is True
    assert trim["force_residual_n"] < 1.0e-8
    assert trim["torque_residual_nm"] < 1.0e-8
    assert len(trim["trim_thrusts_n"]) == 4


def test_allocation_signs() -> None:
    signs = _read("runtime/allocation_sign_validation.json")
    assert signs["matrix_rank"] == 4
    assert signs["collective_sign_valid"] is True
    assert signs["roll_sign_valid"] is True
    assert signs["pitch_sign_valid"] is True
    assert signs["yaw_sign_valid"] is True


def test_single_rotor_force_direction_and_reaction_signs() -> None:
    pulse = _read("runtime/single_rotor_pulse.json")
    assert pulse["rotor_count"] == 4
    assert pulse["all_force_directions_valid"] is True
    assert pulse["all_individual_signs_valid"] is True


def test_motor_dynamics_is_not_instantaneous() -> None:
    motor = _read("runtime/motor_step_response.json")
    assert motor["response_matches_first_order"] is True
    assert motor["instantaneous_jump"] is False
    assert motor["first_step_actual_rad_s"] < motor["command_rad_s"]
    assert motor["thrust_monotonic"] is True


def test_rotor_saturation_is_applied_to_actual_speed_and_thrust() -> None:
    saturation = _read("runtime/rotor_saturation_validation.json")
    assert saturation["saturation_pass"] is True
    assert saturation["speed_within_limits"] is True
    assert saturation["thrust_within_limits"] is True


def test_direct_world_wrench_path_is_disabled() -> None:
    audit = _read("runtime/actuation_path_audit.json")
    assert audit["direct_world_force_command"] is False
    assert audit["direct_world_torque_command"] is False
    assert audit["legacy_direct_wrench_active_in_r5"] is False
    assert audit["rotor_local_axis_force"] is True
    assert audit["rotor_position_force_application"] is True
    assert audit["active_path_audit_pass"] is True


def test_surrogate_and_state_writes_remain_disabled() -> None:
    audit = _read("runtime/actuation_path_audit.json")
    assert audit["python_arm_integrator_present"] is False
    assert audit["manual_reaction_present"] is False
    assert audit["manual_arm_gravity_present"] is False
    assert audit["root_runtime_state_write"] is False
    assert audit["joint_runtime_position_write"] is False
    assert audit["joint_runtime_velocity_write"] is False


def test_rrrp_rotor_coupling_is_native_and_uncontrolled() -> None:
    coupling = _read("runtime/rrrp_rotor_coupling.json")
    assert coupling["rrrp_rotor_coupling_valid"] is True
    assert coupling["rotor_controller_present"] is False
    assert all(item["rotor_command_all_zero"] for item in coupling["cases"])
    assert all(item["joint_response_norm"] > 1.0e-7 for item in coupling["cases"])


def test_headless_5000_step_stability() -> None:
    stability = _read("runtime/headless_stability.json")
    assert stability["required_steps"] == 5000
    assert stability["headless_5000_step_stable"] is True
    assert stability["nan_count"] == 0
    assert stability["inf_count"] == 0
    assert stability["native_exit"] is False
    assert stability["physics_explosion"] is False


def test_r5_readiness_keeps_later_gates_false() -> None:
    readiness = _read("summary/s4_r5_readiness.json")
    assert readiness["final_label"] == "S4_R5_QUADROTOR_ROTOR_ACTUATION_READY"
    assert readiness["head_only_failures"] == 0
    assert readiness["hardware_parameter_validated"] is False
    assert readiness["wind_model_validated"] is False
    assert readiness["contact_dynamics_validated"] is False
    assert readiness["closed_loop_control_validated"] is False
    assert readiness["s4_ready"] is False
