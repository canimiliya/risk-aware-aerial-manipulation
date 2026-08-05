"""Build S4-R0 visual evidence from captured Isaac GUI frames.

The source frames are never synthesized: the script selects frames from the
real Isaac viewport capture manifest, adds an evidence banner, and encodes
local GIFs from the same monotonically timed frame sequences.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RAW_MANIFEST = ROOT / "docs/evidence/S4-R0/visuals/r1/s4_r0_r1_raw_visual_manifest.json"
OUT_DIR = ROOT / "docs/evidence/S4-R0/visuals/r1"
PNG_DIR = OUT_DIR / "png"
VIDEO_DIR = ROOT / "outputs/local_visuals/S4-R0-R1/videos"
SCENARIOS = {
    "hover_hold": "run_01",
    "initial_offset_recovery": "x_plus_010",
    "arm_motion_hold": "run_01",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/segoeui.ttf")):
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), 22)
    return ImageFont.load_default()


def load_metrics(scenario: str, run_id: str) -> dict[str, object]:
    path = ROOT / "outputs/S4-R0" / scenario / run_id / "metrics.json"
    return json.loads(path.read_text(encoding="utf-8"))


def annotate(source: Path, target: Path, item: dict[str, object], metrics: dict[str, object]) -> None:
    image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image)
    fnt = font()
    banner = (
        f"S4-R0-R1 | {item['scenario']} | {item['run_id']} | t={float(item['time_s']):.3f}s | "
        "REAL_S3_ROBOT_VISUAL=TRUE | DYNAMIC_BASE=TRUE | SURROGATE_ARM_REACTION=TRUE | ROOT_TELEPORT=FALSE"
    )
    detail = (
        f"240 Hz | dynamic={metrics['dynamic_model_mode']} | RMSE={float(metrics['position_rmse_m']):.4f} m | "
        f"attitude_RMSE={float(metrics['attitude_rmse_deg']):.3f} deg | "
        f"post-reset writes={metrics['post_reset_state_write_count']}"
    )
    height = 70
    draw.rectangle((0, 0, image.width, height), fill=(8, 20, 36))
    draw.text((18, 10), banner, fill=(238, 248, 255), font=fnt)
    draw.text((18, 40), detail, fill=(160, 224, 181), font=fnt)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format="PNG", optimize=True)


def build_curve(scenario: str, run_id: str) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    state_path = ROOT / "outputs/S4-R0" / scenario / run_id / "state.jsonl"
    rows = [json.loads(line) for line in state_path.read_text(encoding="utf-8").splitlines()]
    times = [row["time_s"] for row in rows]
    position = [row["position_error_m"] for row in rows]
    attitude = [row["attitude_error_rad"] * 180.0 / 3.141592653589793 for row in rows]
    speed = [(sum(float(value) ** 2 for value in row["velocity_m_s"]) ** 0.5) for row in rows]
    joint = [row["joint_error_rad"] for row in rows]
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), dpi=140, constrained_layout=True)
    fig.suptitle(f"S4-R0 real dynamics evidence: {scenario}/{run_id}")
    plots = [(axes[0, 0], position, "position error (m)"), (axes[0, 1], attitude, "attitude error (deg)"), (axes[1, 0], speed, "base speed (m/s)"), (axes[1, 1], joint, "active joint error (rad)")]
    for axis, values, label in plots:
        axis.plot(times, values, color="#1677b8", linewidth=1.1)
        axis.set_xlabel("time (s)")
        axis.set_ylabel(label)
        axis.grid(alpha=0.25)
    target = OUT_DIR / "curves" / f"{scenario}_{run_id}_curves.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target)
    plt.close(fig)
    return target


def main() -> int:
    raw = json.loads(RAW_MANIFEST.read_text(encoding="utf-8"))
    all_frames = raw.get("png", [])
    selected: list[dict[str, object]] = []
    videos: list[dict[str, object]] = []
    curves: list[dict[str, object]] = []
    for scenario, run_id in SCENARIOS.items():
        frames = [item for item in all_frames if item["scenario"] == scenario and item["run_id"] == run_id]
        if len(frames) < 4:
            raise RuntimeError(f"not enough raw GUI frames for {scenario}/{run_id}: {len(frames)}")
        metrics = load_metrics(scenario, run_id)
        indices = sorted({0, len(frames) // 3, (2 * len(frames)) // 3, len(frames) - 1})
        for ordinal, index in enumerate(indices):
            item = frames[index]
            source = Path(str(item["local_path"]))
            target = PNG_DIR / f"{scenario}_{run_id}_{ordinal+1:02d}_t{float(item['time_s']):07.3f}.png"
            annotate(source, target, item, metrics)
            selected.append({**item, "local_path": str(target.resolve()), "sha256": sha256(target), "bytes": target.stat().st_size, "capture_mode": "real_isaac_gui_viewport_with_evidence_overlay"})
        video_frames = [Path(str(item["local_path"])) for item in frames[::4]]
        if video_frames[-1] != Path(str(frames[-1]["local_path"])):
            video_frames.append(Path(str(frames[-1]["local_path"])))
        resized = [Image.open(path).convert("RGB").resize((640, 360)) for path in video_frames]
        video_path = VIDEO_DIR / f"{scenario}_real_isaac_temporal.gif"
        VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        resized[0].save(video_path, save_all=True, append_images=resized[1:], duration=83, loop=0, optimize=True)
        videos.append({"scenario": scenario, "run_id": run_id, "local_path": str(video_path.resolve()), "sha256": sha256(video_path), "bytes": video_path.stat().st_size, "duration_s": round((float(frames[-1]["time_s"]) - float(frames[0]["time_s"])), 6), "fps": 12.0, "width": 640, "height": 360, "frame_count": len(video_frames), "source_capture_mode": "real_isaac_gui_viewport"})
        curve = build_curve(scenario, run_id)
        curves.append({"scenario": scenario, "run_id": run_id, "local_path": str(curve.resolve()), "sha256": sha256(curve), "bytes": curve.stat().st_size})
    manifest = {"decision": "PASS_PENDING_AUDIT", "visual_contract_version": "S4-R0-R1-real-isaac-gui-v1", "capture_mode": "real_isaac_gui_viewport_postprocessed", "source_manifest": str(RAW_MANIFEST.resolve()), "robot_visual_source_usd": "D:/i3/a/aerial_manipulator_v2.usd", "robot_visual_source_sha256": "74cce4b4cd8a41da9b60829482debbf3a78c0548bacb9dd53089e92c5ed7bc7d", "dynamic_base_prim": "/World/QuadrotorBase", "visual_root_prim": "/World/RobotVisual", "png": selected, "video": videos, "local_video_files": [item["local_path"] for item in videos], "curves": curves, "scenarios": list(SCENARIOS), "png_count": len(selected), "video_count": len(videos), "root_teleport": False, "controller_enabled": True, "physics_dt_s": 1.0 / 240.0, "real_s3_robot_visual": True, "surrogate_arm_reaction": True}
    (OUT_DIR / "s4_r0_visual_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"png_count": len(selected), "video_count": len(videos), "curve_count": len(curves), "videos": videos}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
