"""Machine checks for the S4-R6-R4 effort-path audit."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/S4-R6-R4"


def read(relative: str) -> dict:
    return json.loads((EVIDENCE / relative).read_text(encoding="utf-8"))


def test_effort_limits_do_not_explain_r3_response() -> None:
    item = read("effort/q1_effort_limit_manifest.json")
    assert item["command_test_torque_Nm"] == 0.2
    assert item["design_max_effort_Nm"] == 8.0
    assert item["usd_max_effort_Nm"] is None
    assert item["command_exceeds_any_limit"] is False
    assert item["effort_cap_matches_observed_dynamics"] is False


def test_both_effort_paths_are_linear_and_identical() -> None:
    item = read("summary/s4_r6_r4_readiness.json")
    assert item["set_joint_efforts_path"] is True
    assert item["apply_action_path"] is True
    assert item["effort_api_path_match"] is True
    assert item["effort_sweep_linear_below_limit"] is True
    assert item["effort_saturation_present"] is False
    assert item["effort_scaling_present"] is False


def test_fixed_base_m11_reconciles_measured_motion() -> None:
    item = read("effort/q1_oracle_reconciliation.json")
    assert abs(item["M11_fixed_base_motion_inertia_kg_m2"] - 0.0018997916486114264) < 1e-12
    assert abs(item["q1_effective_inertia_r3_schur_complement_kg_m2"] - 0.0004368799492713341) < 1e-12
    assert item["reconciliation"]["measured_effort_matches_motion"] is True
    assert item["reconciliation"]["applied_effort_matches_motion"] is True
    assert item["reconciliation"]["requested_effort_matches_motion"] is True
    assert item["tau_applied_api_Nm"] > 0.199
    assert item["tau_measured_Nm"] > 0.199


def test_r4_does_not_freeze_or_clear_prior_blockers() -> None:
    item = read("summary/s4_r6_r4_readiness.json")
    assert item["allowed_conclusion"] == "ORACLE_INTERPRETATION_BUG_CONFIRMED"
    assert item["final_label"] == "S4_R6_R4_ORACLE_INTERPRETATION_ROOT_CAUSE_CONFIRMED"
    assert item["physx_solver_limitation_confirmed"] is False
    assert item["physics_model_frozen"] is False
    assert item["cleanup_allowed"] is False
    assert item["energy_diagnostic_deferred"] is True
    assert item["preserved_blockers"] == ["BLOCKED_S4_R6_TIMESTEP_CONVERGENCE", "BLOCKED_S4_R6_R2_SOLVER_CONVERGENCE"]
