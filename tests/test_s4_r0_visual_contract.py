import json
from pathlib import Path


def test_visual_manifest_contract():
    root = Path(__file__).parents[1]
    payload = json.loads((root / "docs/evidence/S4-R0/visuals/s4_r0_visual_manifest.json").read_text(encoding="utf-8"))
    assert payload["png_count"] >= 12
    assert payload["video_count"] >= 3
    assert len(payload["curves"]) == 3
    assert payload["physics_dt_s"] == 1 / 240
    assert payload["root_teleport"] is False
    for item in payload["png"] + payload["video"]:
        path = Path(item["local_path"])
        assert path.is_file() and path.stat().st_size == item["bytes"]
