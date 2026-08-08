"""Machine contracts for S4-R6-R5 corrected convergence evidence."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/S4-R6-R5"


def read(relative: str) -> dict:
    return json.loads((EVIDENCE / relative).read_text(encoding="utf-8"))


def test_dof_mapping_and_oracle_are_name_resolved() -> None:
    mapping = read("diagnosis/mass_matrix_dof_mapping.json")
    oracle = read("diagnosis/q1_oracle_reconciliation.json")
    assert mapping["mapping_valid"] is True
    assert mapping["fixed_base"]["q1"]["mass_matrix_index"] == 6
    assert mapping["floating_base"]["q1"]["articulation_dof_index"] == 2
    assert mapping["floating_base"]["q1"]["mass_matrix_row"] == 8
    assert abs(mapping["fixed_base"]["q1_effective_inertia_fixed_kg_m2"] - 0.001899791649) < 1e-9
    assert oracle["reconciled"] is True
    for row in oracle["first_step_by_rate"].values():
        assert abs(row["measured_effort_Nm"] - 0.2) < 1e-4
        assert row["qdd_error_rad_s2"] < 1.0


def test_q1_blocker_is_runtime_convergence_not_superseded_solver_finding() -> None:
    readiness = read("summary/s4_r6_r5_readiness.json")
    superseded = read("diagnosis/superseded_findings.json")
    assert readiness["final_label"] == "BLOCKED_S4_R6_R5_TIMESTEP_CONVERGENCE"
    assert readiness["r3_solver_finding_superseded"] is True
    assert readiness["physics_model_frozen"] is False
    assert readiness["freeze_tag"] is None
    assert superseded["physx_solver_limitation_confirmed"] is False
    assert "BLOCKED_S4_R6_R5_TIMESTEP_CONVERGENCE" in readiness["preserved_blockers"]


def test_runtime_metric_sources_and_upstream_block_are_explicit() -> None:
    convergence = read("runtime/corrected_q1_convergence.json")
    energy = read("runtime/corrected_energy_diagnostic.json")
    stability = read("runtime/final_long_duration_stability.json")
    assert convergence["metric_source"].startswith("runtime state")
    assert convergence["q1_timestep_convergence"] is False
    assert convergence["selected_physics_rate_hz"] is None
    assert energy["status"] == "NOT_RUN_BLOCKED_UPSTREAM_Q1_CONVERGENCE"
    assert stability["status"] == "NOT_RUN_BLOCKED_UPSTREAM_Q1_CONVERGENCE"

