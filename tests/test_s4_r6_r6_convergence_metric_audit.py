import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/S4-R6-R6"


def load(relative):
    return json.loads((EVIDENCE / relative).read_text(encoding="utf-8"))


def test_metric_attribution_and_event_alignment_are_explicit():
    attribution = load("diagnosis/q1_metric_attribution.json")
    events = load("diagnosis/event_alignment_audit.json")
    assert attribution["r5_max_change_source_metric"] == "peak_qdd"
    assert all(value == "peak_qdd" for value in attribution["r5_max_change_source_by_pair"].values())
    assert events["torque_impulse_equivalent"] is True
    assert events["event_alignment_valid"] is True


def test_true_state_gate_blocks_freeze_without_relaxed_thresholds():
    state = load("diagnosis/q1_state_convergence.json")
    readiness = load("summary/s4_r6_r6_readiness.json")
    manifest = load("freeze/physics_model_freeze_manifest.json")
    assert state["q1_true_state_nonconvergence"] is True
    assert state["selected_physics_rate_hz"] is None
    for pair in state["pairs"].values():
        assert "base_position" in pair["metrics"]
        assert "base_orientation_wxyz" in pair["metrics"]
    assert readiness["final_label"] == "BLOCKED_S4_R6_R6_TRUE_STATE_TIMESTEP_NONCONVERGENCE"
    assert readiness["physics_model_frozen"] is False
    assert readiness["cleanup_audit_allowed"] is False
    assert manifest["physics_model_frozen"] is False
    assert manifest["freeze_tag"] is None


def test_supplemental_pose_readback_exists_for_all_rates():
    for rate in (240, 480, 960, 1920):
        payload = json.loads((EVIDENCE / f"diagnosis/state_rate_{rate}hz.json").read_text(encoding="utf-8"))
        assert payload["finite"] is True
        assert "base_position_world_m" in payload["records"][0]
        assert "base_orientation_world_wxyz" in payload["records"][0]


def test_isolation_does_not_use_edge_qdd_or_oracle():
    isolation = load("diagnosis/state_convergence_isolation.json")
    assert isolation["solver_oracle_or_edge_qdd_used"] is False
    assert isolation["first_failure_layer"] == "single_1r"
    assert all(not model["pass"] for model in isolation["models"].values())
