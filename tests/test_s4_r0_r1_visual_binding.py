import json
from pathlib import Path


def test_real_asset_binding_contract_is_explicit():
    root = Path(__file__).parents[1]
    payload = json.loads((root / "docs/evidence/S4-R0/preflight/robot_visual_binding.json").read_text(encoding="utf-8"))
    assert payload["source_sha256"] == "74cce4b4cd8a41da9b60829482debbf3a78c0548bacb9dd53089e92c5ed7bc7d"
    assert payload["stage_prim"] == "/World/RobotVisual"
    assert payload["dynamic_base_prim"] == "/World/QuadrotorBase"
    assert payload["visual_geometry_prim_count"] > 0
    assert payload["root_pose_binding"]
    assert payload["joint_visual_binding"]["active_joints"] == ["m1_1", "m2_1", "m3_1"]
    assert payload["joint_visual_binding"]["passive_joints"]


def test_visual_manifest_uses_real_asset_fields_and_not_procedural_subject():
    root = Path(__file__).parents[1]
    manifest_path = root / "docs/evidence/S4-R0/visuals/r1/s4_r0_r1_raw_visual_manifest.json"
    if not manifest_path.is_file():
        return
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["robot_visual_source_sha256"] == "74cce4b4cd8a41da9b60829482debbf3a78c0548bacb9dd53089e92c5ed7bc7d"
    assert payload["visual_root_prim"] == "/World/RobotVisual"
    assert all(item["real_s3_robot_visual"] for item in payload["png"])
