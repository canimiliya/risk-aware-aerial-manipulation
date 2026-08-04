"""Build local GIFs from retained real Isaac GUI captures and update manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "docs/evidence/S3-R0/visuals/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    video_dir = root / "outputs/local_visuals/S3-R0-R7"
    video_dir.mkdir(parents=True, exist_ok=True)
    videos = []
    for run in ("nominal_gui_r7_corrected_dp", "nominal_repeat_gui_r7_corrected_dp"):
        images = [Image.open(Path(entry["local_path"])) .convert("RGB") for entry in manifest["png"] if entry["source_run"] == run]
        if len(images) != 4:
            raise RuntimeError(f"expected four GUI captures for {run}, got {len(images)}")
        path = video_dir / f"{run}.gif"
        images[0].save(path, save_all=True, append_images=images[1:], duration=400, loop=0, optimize=False)
        videos.append(
            {
                "local_path": str(path.resolve()),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
                "duration_s": 1.6,
                "fps": 2.5,
                "width": images[0].width,
                "height": images[0].height,
                "source_run": run,
                "created_at": manifest["created_at"],
                "format": "GIF",
                "committed": False,
            }
        )
        for image in images:
            image.close()
    manifest["video"] = videos
    manifest["video_count"] = len(videos)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"png_count": manifest["png_count"], "video_count": len(videos), "videos": videos}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
