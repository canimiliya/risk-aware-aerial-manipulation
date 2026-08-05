import json
from pathlib import Path


def test_disabled_collision_reports_unavailable_contact_not_zero():
    root = Path(__file__).parents[1]
    metrics = json.loads((root / "docs/evidence/S4-R0/summary/s4_r0_metrics.json").read_text(encoding="utf-8"))
    assert metrics["physics_contact_available"] is False
    assert metrics["physics_contact_count"] is None
    assert metrics["arm_physics_contact_available"] is False
    assert metrics["arm_safety_evidence"] == "sampled_proxy_clearance_only"
    assert all(run["physics_contact_count"] is None for run in metrics["runs"])
