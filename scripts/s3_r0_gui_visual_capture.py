"""Merge and validate real Isaac GUI state-replay captures for S3-R0-R8.

The Isaac process itself is ``s3_r0_reference_playback.py`` with the optional
visual-capture arguments.  This utility only merges the two per-run manifests,
retains R7 evidence, and rejects missing or fabricated frame/time metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


DANGER_FRAME = 329
DANGER_TIME_S = 1.3708333333333333
DANGEROUS_FRAME = DANGER_FRAME
DANGEROUS_TIME_S = DANGER_TIME_S
FRAME_TOLERANCE = 2
TIME_TOLERANCE_S = 2.0 / 240.0
CAPTURE_MODE = "real_isaac_gui_state_replay"
DANGEROUS_FRAME_TOLERANCE = FRAME_TOLERANCE
DANGEROUS_TIME_TOLERANCE_S = TIME_TOLERANCE_S
FINAL_FRAME = 1254
FINAL_TIME_S = 5.223430863911155


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(entry: dict[str, object]) -> Path:
    return Path(str(entry["local_path"]))


def record_real_gui_capture(
    path: Path,
    *,
    source_run: str,
    frame: int,
    time_s: float,
    view: str,
    state_record: dict[str, object],
) -> dict[str, object]:
    """Build a manifest entry from one real Isaac viewport capture.

    The caller supplies the frame/time immediately after the corresponding
    reference-state playback step; this function never infers or hard-codes a
    final-state timestamp.
    """

    state_bytes = json.dumps(state_record, ensure_ascii=False, sort_keys=True, default=float).encode("utf-8")
    return {
        "local_path": str(path.resolve()),
        "source_run": source_run,
        "source_frame": int(frame),
        "frame": int(frame),
        "source_time_s": float(time_s),
        "time_s": float(time_s),
        "view": view,
        "capture_mode": CAPTURE_MODE,
        "capture_role": "dangerous" if abs(int(frame) - DANGEROUS_FRAME) <= FRAME_TOLERANCE else ("final" if int(frame) == FINAL_FRAME else "timeline"),
        "sha256": _sha256(path),
        "bytes": int(path.stat().st_size),
        "source_state_sha256": hashlib.sha256(state_bytes).hexdigest(),
    }


def _validate_png(entry: dict[str, object]) -> None:
    path = _path(entry)
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"missing or empty PNG: {path}")
    actual_sha = _sha256(path)
    if actual_sha != entry.get("sha256"):
        raise RuntimeError(f"PNG SHA-256 mismatch: {path}")
    if int(entry.get("bytes", -1)) != path.stat().st_size:
        raise RuntimeError(f"PNG byte count mismatch: {path}")
    if entry.get("capture_mode") != CAPTURE_MODE:
        raise RuntimeError(f"PNG is not marked as real state replay: {path}")


def _validate_run(entries: list[dict[str, object]], run: str) -> None:
    if not entries:
        raise RuntimeError(f"no new PNG entries for {run}")
    for entry in entries:
        _validate_png(entry)
        if entry.get("source_run") != run:
            raise RuntimeError(f"source_run mismatch for {run}")
        if int(entry.get("frame", -1)) != int(entry.get("source_frame", -2)):
            raise RuntimeError(f"frame/source_frame mismatch for {run}")
        if float(entry.get("time_s", -1.0)) != float(entry.get("source_time_s", -2.0)):
            raise RuntimeError(f"time/source_time_s mismatch for {run}")
    frames = sorted({int(entry["source_frame"]) for entry in entries if entry.get("view") == "overall"})
    times = [float(next(item["source_time_s"] for item in entries if item.get("view") == "overall" and int(item["source_frame"]) == frame)) for frame in frames]
    if len(frames) < 12 or len(frames) != len(times):
        raise RuntimeError(f"{run} needs at least 12 overall sequence frames")
    if any(a >= b for a, b in zip(frames, frames[1:])) or any(a >= b for a, b in zip(times, times[1:])):
        raise RuntimeError(f"{run} frame/time sequence is not strictly increasing")
    if frames[0] != 0 or frames[-1] != 1254:
        raise RuntimeError(f"{run} sequence must cover frames 0 and 1254")
    if not any(abs(frame - DANGER_FRAME) <= FRAME_TOLERANCE and abs(time_s - DANGER_TIME_S) <= TIME_TOLERANCE_S for frame, time_s in zip(frames, times)):
        raise RuntimeError(f"{run} sequence does not cover the dangerous frame/time")
    for view in ("overall", "close"):
        danger = [entry for entry in entries if entry.get("view") == view and abs(int(entry["source_frame"]) - DANGER_FRAME) <= FRAME_TOLERANCE]
        final = [entry for entry in entries if entry.get("view") == view and int(entry["source_frame"]) == 1254]
        if not danger or not final:
            raise RuntimeError(f"{run} lacks {view} dangerous and final PNG coverage")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nominal-manifest", type=Path, required=True)
    parser.add_argument("--repeat-manifest", type=Path, required=True)
    parser.add_argument("--existing-manifest", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    args = parser.parse_args()

    existing = json.loads(args.existing_manifest.read_text(encoding="utf-8"))
    nominal = json.loads(args.nominal_manifest.read_text(encoding="utf-8"))
    repeat = json.loads(args.repeat_manifest.read_text(encoding="utf-8"))
    nominal_run = "nominal_gui_r8_real_timeline"
    repeat_run = "nominal_repeat_gui_r8_real_timeline"
    nominal_png = [dict(entry) for entry in nominal.get("png", [])]
    repeat_png = [dict(entry) for entry in repeat.get("png", [])]
    _validate_run(nominal_png, nominal_run)
    _validate_run(repeat_png, repeat_run)
    legacy_png = [dict(entry, evidence_revision="R7_LEGACY") for entry in existing.get("png", [])]
    legacy_video = [dict(entry, evidence_revision="R7_LEGACY") for entry in existing.get("video", [])]
    merged = {
        "decision": "PASS",
        "visual_contract_version": "S3-R0-R8-real-timeline-v1",
        "source": "R7 retained evidence plus R8 real Isaac GUI state-replay evidence",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "png_count": len(legacy_png) + len(nominal_png) + len(repeat_png),
        "png": legacy_png + nominal_png + repeat_png,
        "legacy_visual_evidence": {"png": legacy_png, "video": legacy_video},
        "video": [],
        "video_count": 0,
        "r8_contract": {
            "capture_mode": "real_isaac_gui_state_replay",
            "dangerous_frame": DANGER_FRAME,
            "dangerous_time_s": DANGER_TIME_S,
            "frame_tolerance": FRAME_TOLERANCE,
            "time_tolerance_s": TIME_TOLERANCE_S,
            "nominal_run": nominal_run,
            "repeat_run": repeat_run,
        },
    }
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output_manifest.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": merged["decision"], "png_count": merged["png_count"], "nominal_png": len(nominal_png), "repeat_png": len(repeat_png)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
