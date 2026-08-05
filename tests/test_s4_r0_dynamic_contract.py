import json
from pathlib import Path


def test_dynamic_route_contract():
    root = Path(__file__).parents[1]
    payload = json.loads((root / "docs/evidence/S4-R0/preflight/dynamic_route_decision.json").read_text(encoding="utf-8"))
    assert payload["dynamic_surrogate"] is True
    assert payload["full_closed_chain_dynamics"] is False
    assert payload["floating_base"] is True
    assert payload["control_interface"] == "BODY_WRENCH_PLUS_JOINT_TARGETS"
    assert payload["active_joints"] == ["m1_1", "m2_1", "m3_1"]
