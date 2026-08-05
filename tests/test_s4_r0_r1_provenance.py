import json
from pathlib import Path


def test_mass_provenance_is_finite_positive_and_usd_sourced():
    root = Path(__file__).parents[1]
    payload = json.loads((root / "docs/evidence/S4-R0/preflight/arm_mass_inertia_provenance.json").read_text(encoding="utf-8"))
    assert payload["pass"] is True
    assert payload["source_sha256"] == "74cce4b4cd8a41da9b60829482debbf3a78c0548bacb9dd53089e92c5ed7bc7d"
    assert payload["links"]
    assert all(float(item["mass_kg"]) > 0.0 for item in payload["links"])
    assert all(len(item["center_of_mass_m"]) == 3 for item in payload["links"])
    assert all(len(item["diagonal_inertia_kg_m2"]) == 3 for item in payload["links"])
    assert "converted into mass" in payload["derivation"]


def test_mass_accounting_contract_has_no_double_count():
    root = Path(__file__).parents[1]
    config = (root / "configs/s4/s4_r0_nominal_control.yaml").read_text(encoding="utf-8")
    assert "BASE_PLUS_ARM_SEPARATE" in config
    assert "mass_derivation" not in config
    assert "JointEquivalentInertia" not in config
    metrics = json.loads((root / "docs/evidence/S4-R0/summary/s4_r0_metrics.json").read_text(encoding="utf-8"))
    assert abs(metrics["total_system_mass_kg"] - (metrics["base_mass_kg"] + metrics["arm_mass_kg"])) <= 1e-12
    assert metrics["hover_feedforward_mass_kg"] == metrics["total_system_mass_kg"]
