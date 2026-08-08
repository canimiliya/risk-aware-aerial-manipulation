from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/S4-R6-R2"


def read(relative: str) -> dict:
    return json.loads((EVIDENCE / relative).read_text(encoding="utf-8"))


def test_diagnosis_and_protocol_audit_are_explicit() -> None:
    diagnosis = read("diagnosis/convergence_failure_diagnosis.json")
    protocol = read("diagnosis/timebase_protocol_audit.json")
    assert diagnosis["failed_metric_count"] > 0
    assert protocol["PHYSICAL_TIME_EQUIVALENT"] is True
    assert protocol["PULSE_DURATION_EQUIVALENT"] is True
    assert protocol["PULSE_IMPULSE_EQUIVALENT"] is True
    assert protocol["INITIAL_STATE_EQUIVALENT"] is True


def test_motor_discretization_is_analytic_and_unchanged() -> None:
    audit = read("diagnosis/motor_discretization_audit.json")
    assert audit["motor_discretization_valid"] is True
    assert audit["parameter_preservation"]["unchanged"] is True
    assert all(item["matches_analytic_solution"] for item in audit["rates"])


def test_corrected_convergence_is_not_promoted() -> None:
    corrected = read("runtime/corrected_timestep_convergence.json")
    reference = read("runtime/reference_960_to_1920_convergence.json")
    sweep = read("runtime/solver_convergence_sweep.json")
    assert corrected["timestep_convergence_valid"] is False
    assert reference["reference_convergence_960_to_1920_valid"] is False
    assert sweep["solver_convergence_valid"] is False
    assert all(item["timestep_convergence_valid"] is False for item in sweep["configurations"])


def test_energy_is_warning_not_hidden_pass() -> None:
    method = read("diagnosis/energy_diagnostic_method_audit.json")
    result = read("runtime/final_energy_diagnostic.json")
    assert method["method_contract_valid"] is True
    assert result["energy_diagnostic_method_valid"] is True
    assert result["initial_energy_j"] > 0.0
    assert result["energy_diagnostic"] == "WARNING"
    assert result["energy_pass"] is False
