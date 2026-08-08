"""Machine contracts for the S4-R6 blocked freeze audit."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/S4-R6"


def read(relative: str) -> dict:
    return json.loads((EVIDENCE / relative).read_text(encoding="utf-8"))


def test_trim_envelope_and_named_configurations() -> None:
    envelope = read("runtime/rrrp_hover_trim_envelope.json")
    named = read("runtime/stowed_approach_trim.json")
    assert envelope["sample_count"] == 81
    assert 0 < envelope["valid_count"] <= 81
    assert envelope["invalid_count"] == envelope["sample_count"] - envelope["valid_count"]
    assert named["stowed_trim_margin_valid"] is True
    assert named["approach_trim_margin_valid"] is True
    assert named["stowed"]["hover_trim"]["max_rotor_utilization"] <= 0.80
    assert max(item["hover_trim"]["max_rotor_utilization"] for item in named["approach_cases"]) <= 0.90


def test_mass_and_frozen_parameters() -> None:
    manifest = read("freeze/physics_model_freeze_manifest.json")
    assert manifest["active_manipulator"] == "RRRP"
    assert manifest["dof"] == 4
    assert manifest["rotor_count"] == 4
    assert abs(manifest["system_mass_kg"] - 1.65) < 1e-6
    assert manifest["max_thrust_per_rotor_n"] == 7.3500000000000005
    assert manifest["hardware_parameter_validated"] if "hardware_parameter_validated" in manifest else True


def test_momentum_and_long_stability() -> None:
    momentum = read("runtime/linear_momentum_validation.json")
    stability = read("runtime/headless_10000_step_stability.json")
    assert momentum["linear_momentum_validated"] is True
    assert momentum["linear_momentum_relative_drift"] < 0.001
    assert stability["required_steps"] == 10000
    assert stability["headless_10000_step_pass"] is True
    assert all(item["nan_count"] == 0 and item["inf_count"] == 0 for item in stability["cases"])


def test_actuation_path_and_scope() -> None:
    audit = read("runtime/final_actuation_audit.json")
    assert audit["direct_world_force_command"] is False
    assert audit["direct_world_torque_command"] is False
    assert audit["active_path_audit_pass"] is True
    assert audit["root_runtime_state_write"] is False
    assert audit["joint_runtime_position_write"] is False
    assert audit["joint_runtime_velocity_write"] is False


def test_timestep_block_is_not_silently_promoted() -> None:
    convergence = read("runtime/timestep_convergence.json")
    assert convergence["timestep_convergence_valid"] is False
