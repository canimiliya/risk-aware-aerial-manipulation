"""Machine contracts for the independent S4-R4 RRRP evidence package."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/S4-R4"


def _read(relative: str) -> dict:
    return json.loads((EVIDENCE / relative).read_text(encoding="utf-8"))


def test_rrrp_design_contract() -> None:
    design = _read("design/rrrp_design_manifest.json")
    assert design["architecture"] == "RRRP_serial_manipulator"
    assert design["dof_count"] == 4
    assert design["revolute_count"] == 3
    assert design["prismatic_count"] == 1
    assert design["parameter_provenance"] == "ENGINEERING_NOMINAL"
    assert design["provisional"] is True


def test_mass_inertia_contract() -> None:
    design = _read("design/rrrp_design_manifest.json")
    masses = _read("design/mass_inertia_manifest.json")
    assert design["all_dynamic_links_positive_mass"] is True
    assert design["all_inertias_physically_valid"] is True
    assert masses["all_positive_mass"] is True
    assert masses["all_inertia_physically_valid"] is True
    assert all(float(item["mass_kg"]) > 0.0 for item in masses["records"])


def test_joint_manifest_is_native_tree() -> None:
    joints = _read("design/joint_manifest.json")
    assert joints["native_dof_count_per_articulation"] == 4
    assert sum(item["type"] == "revolute" for item in joints["joints"]) == 3
    assert sum(item["type"] == "prismatic" for item in joints["joints"]) == 1
    assert joints["tree_structure"] is True


def test_fixed_and_floating_articulations_are_present() -> None:
    runtime = _read("summary/s4_r4_runtime_result.json")
    assert runtime["fixed_articulation_present"] is True
    assert runtime["floating_articulation_present"] is True
    assert runtime["fixed_base_2000_step_stable"] is True
    assert runtime["floating_base_2000_step_stable"] is True


def test_native_effort_responses_and_base_reaction() -> None:
    runtime = _read("summary/s4_r4_runtime_result.json")
    for key in ("q1_native_response", "q2_native_response", "q3_native_response", "p_native_response", "base_dynamic_response_from_arm"):
        assert runtime[key] is True


def test_prismatic_limit_cases() -> None:
    validation = _read("runtime/prismatic_validation.json")
    assert len(validation["cases"]) == 3
    assert validation["all_cases_within_limit"] is True
    assert [round(float(item["requested_d_m"]), 3) for item in validation["cases"]] == [0.0, 0.04, 0.08]


def test_state_write_audit_disables_python_state_playback() -> None:
    audit = _read("runtime/state_write_audit.json")
    assert audit["python_arm_integrator_present"] is False
    assert audit["manual_reaction_present"] is False
    assert audit["manual_arm_gravity_present"] is False
    assert audit["root_runtime_state_write"] is False
    assert audit["joint_runtime_position_write"] is False
    assert audit["joint_runtime_velocity_write"] is False
    assert audit["post_reset_effort_actions_only"] is True


def test_momentum_gate_is_machine_checked() -> None:
    momentum = _read("runtime/momentum_validation.json")
    assert momentum["gravity_xyz"] == [0.0, 0.0, 0.0]
    assert momentum["external_wrench"] is False
    assert momentum["linear_momentum_relative_drift"] < 0.01
    assert momentum["pass"] is True


def test_scope_limits_remain_explicit() -> None:
    readiness = _read("summary/s4_r4_readiness.json")
    assert readiness["active_manipulator"] == "RRRP"
    assert readiness["legacy_delta_asset"] is True
    assert readiness["active_manipulator_is_delta"] is False
    assert readiness["full_rotor_actuation"] is False
    assert readiness["hardware_parameter_validated"] is False
    assert readiness["contact_dynamics_validated"] is False
    assert readiness["s4_ready"] is False
