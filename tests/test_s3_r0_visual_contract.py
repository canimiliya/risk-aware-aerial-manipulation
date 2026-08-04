from __future__ import annotations

from pathlib import Path
import hashlib

import pytest
from PIL import Image

from scripts.s3_r0_visual_video_manifest import _sequence


def test_same_time_view_slide_is_rejected(tmp_path: Path) -> None:
    run = "nominal_gui_r8_real_timeline"
    frames = [0, 100, 200, 280, 327, 329, 331, 400, 600, 800, 1000, 1150, 1254]
    entries = []
    for frame in frames:
        path = tmp_path / f"frame_{frame}.png"
        Image.new("RGB", (8, 8), color=(frame % 255, 10, 20)).save(path)
        entries.append(
            {
                "source_run": run,
                "view": "overall",
                "capture_mode": "real_isaac_gui_state_replay",
                "source_frame": frame,
                "source_time_s": 1.0,
                "local_path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
        )
    with pytest.raises(RuntimeError, match="duplicate source frame/time"):
        _sequence({"png": entries}, run)


def test_four_same_time_views_are_not_a_timeline(tmp_path: Path) -> None:
    run = "nominal_gui_r8_real_timeline"
    entries = []
    for view in ("overall", "side", "top", "close"):
        path = tmp_path / f"{view}.png"
        Image.new("RGB", (8, 8), color=(20, 30, 40)).save(path)
        entries.append(
            {
                "source_run": run,
                "view": view,
                "capture_mode": "real_isaac_gui_state_replay",
                "source_frame": 1254,
                "source_time_s": 5.223430863911155,
                "local_path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
        )
    with pytest.raises(RuntimeError, match="requires at least 12 real overall frames"):
        _sequence({"png": entries}, run)
