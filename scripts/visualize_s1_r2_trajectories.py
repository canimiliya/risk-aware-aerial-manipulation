#!/usr/bin/env python3
"""Generate small static/GIF views of exported base and arm trajectories."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np


RUNS = {
    "write": "write_official",
    "grasp": "grasp_official",
    "lift": "lift_official",
    "waypoint_variant": "grasp_waypoint_variant_01",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def plot_run(label: str, directory: Path, figures: Path, videos: Path) -> dict:
    base = np.load(directory / "sampled_trajectory.npz")
    arm = np.load(directory / "sampled_trajectory_arm.npz")
    base_pos = base["position"]
    arm_pos = arm["position"]
    fig = plt.figure(figsize=(6.4, 4.8), dpi=100)
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(base_pos[:, 0], base_pos[:, 1], base_pos[:, 2], label="base /trajectory", color="#1769aa", linewidth=2.0)
    ax.plot(arm_pos[:, 0], arm_pos[:, 1], arm_pos[:, 2], label="arm /trajectory_arm", color="#d95f02", linewidth=1.6, linestyle="--")
    ax.scatter(*base_pos[0], color="#1b9e77", s=35, label="start")
    ax.scatter(*base_pos[-1], color="#d62728", s=35, label="end")
    ax.set_title(f"S1-R2 {label}")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.legend(loc="best", fontsize=7)
    fig.tight_layout()
    figures.mkdir(parents=True, exist_ok=True)
    videos.mkdir(parents=True, exist_ok=True)
    png = figures / f"{label}.png"
    fig.savefig(png, bbox_inches="tight")

    # Limit animation to at most 40 frames while retaining the complete path in the PNG.
    frame_count = min(40, len(base_pos))
    indices = np.linspace(1, len(base_pos), frame_count, dtype=int)
    animated_base, = ax.plot([], [], [], color="#1769aa", linewidth=2.5)
    animated_arm, = ax.plot([], [], [], color="#d95f02", linewidth=1.8, linestyle="--")

    def update(frame: int):
        end = int(indices[frame])
        animated_base.set_data(base_pos[:end, 0], base_pos[:end, 1])
        animated_base.set_3d_properties(base_pos[:end, 2])
        arm_end = min(end, len(arm_pos))
        animated_arm.set_data(arm_pos[:arm_end, 0], arm_pos[:arm_end, 1])
        animated_arm.set_3d_properties(arm_pos[:arm_end, 2])
        return animated_base, animated_arm

    gif = videos / f"{label}.gif"
    animation = FuncAnimation(fig, update, frames=frame_count, interval=100, blit=False)
    animation.save(gif, writer=PillowWriter(fps=10))
    plt.close(fig)
    return {
        "file": gif.name,
        "bytes": gif.stat().st_size,
        "sha256": sha256(gif),
        "fps": 10,
        "duration_s": frame_count / 10.0,
        "source_trajectory": str(directory).replace("\\", "/"),
        "static_png": str(png).replace("\\", "/"),
        "generation_script": "scripts/visualize_s1_r2_trajectories.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.repo.resolve()
    trajectory_root = root / "data/trajectories/S1-R2"
    figures = root / "outputs/figures/S1-R2"
    videos = root / "outputs/videos/S1-R2"
    entries = [plot_run(label, trajectory_root / directory, figures, videos) for label, directory in RUNS.items()]
    manifest = {
        "format": "GIF",
        "entries": entries,
        "note": "Videos are local evidence artifacts and are intentionally not committed; small static PNGs and this manifest are committed.",
    }
    (videos / "video_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
