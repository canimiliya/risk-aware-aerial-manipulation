"""Create chronological local GIFs from real Isaac GUI state-replay frames."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


DANGER_FRAME = 329
DANGER_TIME_S = 1.3708333333333333
FRAME_TOLERANCE = 2
TIME_TOLERANCE_S = 2.0 / 240.0
MIN_VIDEO_FRAMES = 12
VISUAL_CONTRACT_VERSION = "S3-R0-R8-real-timeline-v1"


def inspect_gif(path: Path) -> dict[str, object]:
    """Read physical GIF metadata independently of the manifest claims."""

    hashes: set[str] = set()
    durations_ms: list[int] = []
    with Image.open(path) as image:
        width, height = image.size
        frame_count = int(getattr(image, "n_frames", 1))
        for index in range(frame_count):
            image.seek(index)
            durations_ms.append(int(image.info.get("duration", 0)))
            hashes.add(hashlib.sha256(image.convert("RGB").tobytes()).hexdigest())
    duration_s = sum(durations_ms) / 1000.0
    return {
        "width": width,
        "height": height,
        "frame_count": frame_count,
        "duration_s": duration_s,
        "fps": (frame_count / duration_s) if duration_s > 0 else 0.0,
        "distinct_frame_count": len(hashes),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sequence(manifest: dict[str, object], run: str) -> tuple[list[dict[str, object]], list[int], list[float]]:
    entries = [entry for entry in manifest.get("png", []) if entry.get("source_run") == run and entry.get("view") == "overall" and entry.get("capture_mode") == "real_isaac_gui_state_replay"]
    entries.sort(key=lambda entry: int(entry["source_frame"]))
    if len(entries) < MIN_VIDEO_FRAMES:
        raise RuntimeError(f"{run} requires at least 12 real overall frames")
    frames = [int(entry["source_frame"]) for entry in entries]
    times = [float(entry["source_time_s"]) for entry in entries]
    if len(set(frames)) != len(frames) or len(set(times)) != len(times):
        raise RuntimeError(f"{run} contains duplicate source frame/time values")
    if any(a >= b for a, b in zip(frames, frames[1:])) or any(a >= b for a, b in zip(times, times[1:])):
        raise RuntimeError(f"{run} is not chronological")
    if frames[0] != 0 or frames[-1] != 1254:
        raise RuntimeError(f"{run} does not cover the start and final frame")
    if not any(abs(frame - DANGER_FRAME) <= FRAME_TOLERANCE and abs(time_s - DANGER_TIME_S) <= TIME_TOLERANCE_S for frame, time_s in zip(frames, times)):
        raise RuntimeError(f"{run} does not cover the dangerous time")
    for entry in entries:
        path = Path(str(entry["local_path"]))
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"missing video source PNG: {path}")
        if _sha256(path) != entry.get("sha256") or path.stat().st_size != int(entry.get("bytes", -1)):
            raise RuntimeError(f"video source PNG hash/size mismatch: {path}")
    return entries, frames, times


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("docs/evidence/S3-R0/visuals/manifest.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/local_visuals/S3-R0-R8"))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    videos: list[dict[str, object]] = []
    for run in ("nominal_gui_r8_real_timeline", "nominal_repeat_gui_r8_real_timeline"):
        entries, frames, times = _sequence(manifest, run)
        images = [Image.open(Path(str(entry["local_path"]))).convert("RGB") for entry in entries]
        path = args.output_dir / f"{run}.gif"
        frame_duration_ms = 100
        images[0].save(path, save_all=True, append_images=images[1:], duration=frame_duration_ms, loop=0, optimize=False)
        for image in images:
            image.close()
        videos.append(
            {
                "local_path": str(path.resolve()),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
                "duration_s": len(images) * frame_duration_ms / 1000.0,
                "fps": 1000.0 / frame_duration_ms,
                "width": Image.open(path).width,
                "height": Image.open(path).height,
                "source_run": run,
                "frame_count": len(entries),
                "source_frames": frames,
                "source_times_s": times,
                "source_image_sha256": [str(entry["sha256"]) for entry in entries],
                "source_state_sha256": [str(entry["source_state_sha256"]) for entry in entries],
                "time_start_s": times[0],
                "time_end_s": times[-1],
                "camera_view": "overall",
                "visual_contract_version": VISUAL_CONTRACT_VERSION,
                "motion_detected": len({str(entry["sha256"]) for entry in entries}) >= 2 and len({str(entry["source_state_sha256"]) for entry in entries}) >= 2,
                "capture_mode": "real_isaac_gui_state_replay",
                "chronological": True,
                "covers_start": frames[0] == 0,
                "covers_dangerous_time": any(abs(frame - DANGER_FRAME) <= FRAME_TOLERANCE and abs(time_s - DANGER_TIME_S) <= TIME_TOLERANCE_S for frame, time_s in zip(frames, times)),
                "covers_final": frames[-1] == 1254,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "format": "GIF",
                "committed": False,
            }
        )
    manifest["video"] = videos
    manifest["video_count"] = len(videos)
    manifest["decision"] = "PASS"
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": manifest["decision"], "png_count": manifest["png_count"], "video_count": len(videos), "videos": videos}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
