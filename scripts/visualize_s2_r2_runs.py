from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter

from planner_bridge.export.sampling import load_captured_message, sample_message
from planner_bridge.scenes.generate_s2_r2_crossarm_map import build_points


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "docs/evidence/S2-R2/runtime"
OUT = ROOT / "docs/evidence/S2-R2/visuals"
RUNS = {"smoke_free": "smoke_free_run_08", "loose": "loose_run_01", "nominal": "nominal_run_01", "nominal_repeat": "nominal_repeat_01", "narrow": "narrow_diagnostic_01"}


def trajectory(variant: str, arm: bool = False):
    payload = load_captured_message(RUNTIME / RUNS[variant] / ("trajectory_arm.json" if arm else "trajectory.json"))
    return sample_message(payload, 0.01)


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=150)
    plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    colors = {"smoke_free": "#607d8b", "loose": "#2e7d32", "nominal": "#1565c0", "nominal_repeat": "#ef6c00", "narrow": "#8e24aa"}
    sampled = {name: trajectory(name) for name in RUNS}
    arms = {name: trajectory(name, arm=True) for name in RUNS}
    points = np.asarray(build_points("nominal"), dtype=float)

    fig = plt.figure(figsize=(7, 5)); ax = fig.add_subplot(projection="3d")
    ax.scatter(points[:, 0], points[:, 1], points[:, 2], s=1, alpha=.08, color="black")
    for name, data in sampled.items(): ax.plot(*data["position"].T, color=colors[name], label=name)
    ax.set_title("S2-R2 real AM-Planner base trajectories"); ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("z [m]"); ax.legend(fontsize=7)
    save(fig, "01_base_trajectories_3d")

    fig, axes = plt.subplots(3, 1, figsize=(7, 6), sharex=True)
    for axis, label in zip(axes, "xyz"):
        for name, data in sampled.items(): axes["xyz".index(label)].plot(data["time"], data["position"][:, "xyz".index(label)], color=colors[name], label=name)
        axis.set_ylabel(f"{label} [m]")
    axes[0].legend(fontsize=7, ncol=3); axes[-1].set_xlabel("time [s]"); fig.suptitle("Base position versus time")
    save(fig, "02_base_position_time")

    fig = plt.figure(figsize=(7, 5)); ax = fig.add_subplot(projection="3d")
    ax.scatter(points[:, 0], points[:, 1], points[:, 2], s=1, alpha=.08, color="black")
    for name, data in arms.items(): ax.plot(*data["position"].T, color=colors[name], label=name)
    ax.set_title("S2-R2 real Cartesian arm trajectories"); ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("z [m]"); ax.legend(fontsize=7)
    save(fig, "03_arm_cartesian_trajectories_3d")

    validation = json.loads((ROOT / "docs/evidence/S2-R2/validation/real_run_validation.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(7, 4.5))
    names = list(RUNS); x = np.arange(len(names)); width = .35
    base_clear = [validation["variants"][n]["frequencies"]["100Hz"]["proxy_clearance"]["base_min_clearance_m"] for n in names]
    arm_clear = [validation["variants"][n]["frequencies"]["100Hz"]["proxy_clearance"]["arm_min_clearance_m"] for n in names]
    ax.bar(x-width/2, base_clear, width, label="base proxy"); ax.bar(x+width/2, arm_clear, width, label="arm proxy"); ax.axhline(.01, color="red", linestyle="--", label="gate 0.010 m")
    ax.set_xticks(x, names, rotation=20); ax.set_ylabel("minimum proxy clearance [m]"); ax.set_title("Independent point-cloud proxy clearance"); ax.legend(fontsize=8)
    save(fig, "04_proxy_clearance")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    n = sampled["nominal"]; r = sampled["nominal_repeat"]
    ax.plot(n["position"][:, 0], n["position"][:, 1], label="nominal", color="#1565c0"); ax.plot(r["position"][:, 0], r["position"][:, 1], "--", label="repeat", color="#ef6c00")
    ax.set_aspect("equal"); ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_title("Nominal repeat base XY overlay"); ax.legend()
    save(fig, "05_nominal_repeat_overlay")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for name, data in sampled.items(): ax.plot(data["time"], np.linalg.norm(data["velocity"], axis=1), color=colors[name], label=name)
    ax.set_xlabel("time [s]"); ax.set_ylabel("speed [m/s]"); ax.set_title("Base speed profiles"); ax.legend(fontsize=7, ncol=3)
    save(fig, "06_base_speed_profiles")

    def make_gif(name: str, arm: bool) -> None:
        data = arms["nominal"] if arm else sampled["nominal"]
        fig = plt.figure(figsize=(6, 4)); ax = fig.add_subplot(projection="3d")
        ax.scatter(points[:, 0], points[:, 1], points[:, 2], s=1, alpha=.06, color="black")
        line, = ax.plot([], [], [], color="#1565c0", linewidth=2)
        dot, = ax.plot([], [], [], "o", color="#d32f2f")
        ax.set_xlim(points[:, 0].min()-0.2, points[:, 0].max()+0.2); ax.set_ylim(points[:, 1].min()-0.2, points[:, 1].max()+0.2); ax.set_zlim(0, max(1.8, points[:, 2].max()+.1)); ax.set_title("Nominal real trajectory animation")
        stride = max(1, len(data["time"]) // 80)
        frames = list(range(0, len(data["time"]), stride)) + [len(data["time"])-1]
        def update(i):
            p = data["position"][:frames[i]+1]; line.set_data(p[:, 0], p[:, 1]); line.set_3d_properties(p[:, 2]); q = p[-1]; dot.set_data([q[0]], [q[1]]); dot.set_3d_properties([q[2]]); return line, dot
        animation = FuncAnimation(fig, update, frames=len(frames), interval=40, blit=False)
        animation.save(OUT / f"{name}.gif", writer=PillowWriter(fps=20)); plt.close(fig)

    make_gif("07_nominal_base_animation", False)
    make_gif("08_nominal_arm_animation", True)
    manifest = {"png": sorted(p.name for p in OUT.glob("*.png")), "gif": sorted(p.name for p in OUT.glob("*.gif")), "source": "captured ROS PolynomialTrajectory messages; no synthetic trajectory data"}
    (OUT / "visual_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
