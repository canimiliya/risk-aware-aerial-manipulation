import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_r2_native_failure_manifest_is_honest_and_complete():
    payload = json.loads((ROOT / "docs/evidence/S4-R0/visuals/r2/s4_r0_r2_visual_manifest.json").read_text(encoding="utf-8"))
    assert payload["available"] is False
    assert payload["pass"] is False
    assert payload["r2_png_count"] == 0
    assert payload["r2_video_count"] == 0
    assert payload["r2_curve_count"] == 0
    assert payload["legacy_preserved_evidence"]["classification"] == "legacy_S4-R0_preserved_not_promoted_to_R2"


def test_r2_crash_matrix_records_each_independent_probe():
    payload = json.loads((ROOT / "docs/evidence/S4-R0/visuals/r2/visual_crash_matrix.json").read_text(encoding="utf-8"))
    assert [item["probe_id"] for item in payload["probes"]] == ["P0", "P1", "P2", "P3"]
    assert all("command" in item and "last_phase_marker" in item and "kit_log_path" in item for item in payload["probes"])
    assert "Usd.TimeCode" in " ".join(payload["forbidden_routes_verified_absent"])


def test_r2_cache_failure_does_not_claim_visual_geometry():
    payload = json.loads((ROOT / "docs/evidence/S4-R0/visuals/r2/visual_cache_manifest.json").read_text(encoding="utf-8"))
    assert payload["decision"] == "BLOCKED_S4_R0_R2_VISUAL_CACHE_BUILD_FAILED"
    assert payload["hard_gates"]["mesh_count_gt_0"] is False
    assert payload["hard_gates"]["physics_schemas_zero"] is False


def test_r2_animation_script_does_not_use_timeline_time_samples():
    source = (ROOT / "scripts/s4_r0_r2_live_visual_capture.py").read_text(encoding="utf-8")
    assert "Usd.TimeCode" not in source
    assert "SetTimeCode" not in source
    assert "live_physics" in (ROOT / "scripts/s4_r0_nominal_dynamics_demo.py").read_text(encoding="utf-8")


def test_r2_base_head_regression_has_no_head_only_failure():
    payload = json.loads((ROOT / "docs/evidence/S4-R0/tests/base_vs_head_pytest.json").read_text(encoding="utf-8"))
    assert payload["head_only_failures"] == []
    assert payload["hard_gate_head_only_failures_zero"] is True
