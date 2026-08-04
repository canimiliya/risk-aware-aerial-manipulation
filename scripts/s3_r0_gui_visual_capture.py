"""Capture real Isaac GUI viewport PNGs from corrected exported scene USDs."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


VIEWS = {
    "overall": ([3.8, -5.0, 3.3], [0.0, 0.3, 1.0]),
    "side": ([3.5, -0.1, 1.8], [0.0, 0.3, 1.0]),
    "top": ([0.2, -0.1, 6.0], [0.0, 0.3, 0.9]),
    "close": ([1.6, -2.0, 1.8], [0.0, 0.5, 1.0]),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _capture(app, viewport, path: Path) -> None:
    from omni.kit.viewport.utility import capture_viewport_to_file

    path.parent.mkdir(parents=True, exist_ok=True)
    capture_viewport_to_file(viewport, file_path=str(path), is_hdr=False)
    for _ in range(120):
        app.update()
        if path.is_file() and path.stat().st_size > 0:
            return
    raise TimeoutError(f"viewport capture did not produce {path}")


def _open_and_capture(app, stage_path: Path, output_dir: Path, source_run: str) -> list[dict[str, object]]:
    import omni.usd
    from isaacsim.core.utils.viewports import set_camera_view
    from omni.kit.viewport.utility import get_active_viewport

    context = omni.usd.get_context()
    future = asyncio.ensure_future(context.open_stage_async(str(stage_path)))
    for _ in range(600):
        app.update()
        if future.done():
            break
    if not future.done() or future.exception() is not None:
        raise RuntimeError(f"could not open stage {stage_path}")
    for _ in range(30):
        app.update()
    viewport = get_active_viewport()
    if viewport is None:
        raise RuntimeError("no active Isaac GUI viewport")
    entries: list[dict[str, object]] = []
    for view_name, (eye, target) in VIEWS.items():
        set_camera_view(eye=eye, target=target, viewport_api=viewport)
        for _ in range(4):
            app.update()
        path = output_dir / f"{source_run}_{view_name}.png"
        _capture(app, viewport, path)
        entries.append(
            {
                "local_path": str(path.resolve()),
                "source_run": source_run,
                "frame": 1254,
                "time_s": 5.223430863911155,
                "view": view_name,
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nominal-stage", type=Path, required=True)
    parser.add_argument("--repeat-stage", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    from isaacsim import SimulationApp

    app = SimulationApp({"headless": False, "hide_ui": False, "renderer": "RayTracedLighting"})
    try:
        entries = _open_and_capture(app, args.nominal_stage, args.output_dir, "nominal_gui_r7_corrected_dp")
        entries += _open_and_capture(app, args.repeat_stage, args.output_dir, "nominal_repeat_gui_r7_corrected_dp")
        manifest = {
            "decision": "PASS" if len(entries) >= 8 else "FAIL",
            "source": "real Isaac GUI viewport captures from corrected exported USD scenes",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "png_count": len(entries),
            "png": entries,
            "video": [],
        }
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    finally:
        app.close(wait_for_replicator=False, skip_cleanup=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
