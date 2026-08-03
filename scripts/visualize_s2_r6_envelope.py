"""Generate the S2-R6 acceptance figures and local-only animations."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter

from planner_bridge.execution.official_delta_kinematics import official_ik
from planner_bridge.execution.playback_validator import sample_raw


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence/S2-R6/envelope/figures"
RUNTIME = ROOT / "docs/evidence/S2-R6/runtime"
SUMMARY = ROOT / "docs/evidence/S2-R6/final_validation"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def arm(run: str) -> dict:
    return sample_raw(RUNTIME / run / "trajectory_arm.json", 2000, arm=True)


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=160)
    plt.close(fig)


def path_plot(ax, data: dict, label: str, color: str) -> None:
    p = np.asarray(data["position"], dtype=float)
    ax.plot(p[:, 0], p[:, 2], label=label, color=color, linewidth=1.2)
    ax.scatter([p[0, 0], p[-1, 0]], [p[0, 2], p[-1, 2]], color=color, s=14)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    envelope = load(ROOT / "docs/evidence/S2-R6/envelope/anchor_balls.json")
    summary = load(SUMMARY / "candidate_summary.json")
    freq = load(SUMMARY / "frequency_convergence.json")
    p = np.asarray(envelope["centers_m"], dtype=float)

    fig = plt.figure(figsize=(7, 5))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(p[:, 0], p[:, 1], p[:, 2], color="#1565c0", linewidth=2, label="ordered centers")
    ax.scatter(p[:, 0], p[:, 1], p[:, 2], s=8, color="#ef6c00", label="64 anchor centers")
    ax.set(xlabel="x (m)", ylabel="y (m)", zlabel="z (m)", title="S2-R6 Cartesian execution envelope")
    ax.legend(loc="best")
    save(fig, "01_anchor_ball_envelope.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    path_plot(ax, arm("round1_disabled"), "Round1 disabled", "#d32f2f")
    path_plot(ax, arm("nominal_100w0"), "100w0 enabled", "#2e7d32")
    ax.set(xlabel="arm x (m)", ylabel="arm z (m)", title="Round1 arm path: baseline versus enabled barrier")
    ax.legend()
    save(fig, "02_arm_path_baseline_enabled.png")

    before = np.asarray([official_ik(x) for x in arm("round1_disabled")["position"]])
    after = np.asarray([official_ik(x) for x in arm("nominal_100w0")["position"]])
    fig, ax = plt.subplots(figsize=(7, 4))
    for i, name in enumerate(("q1", "q2", "q3")):
        ax.plot(before[:, i], linestyle="--", linewidth=1, label=f"{name} disabled")
        ax.plot(after[:, i], linewidth=1, label=f"{name} enabled")
    ax.axhline(0, color="black", linewidth=.7)
    ax.axhline(np.pi / 2, color="black", linewidth=.7)
    ax.set(xlabel="sample", ylabel="joint angle (rad)", title="Joint trajectories before/after")
    ax.legend(ncol=2, fontsize=8)
    save(fig, "03_q_before_after.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(np.min(np.stack([before, np.pi / 2 - before]), axis=0).min(axis=1), label="disabled")
    ax.plot(np.min(np.stack([after, np.pi / 2 - after]), axis=0).min(axis=1), label="enabled")
    ax.axhline(0, color="black", linewidth=.7)
    ax.set(xlabel="sample", ylabel="joint margin (rad)", title="Minimum joint margin")
    ax.legend()
    save(fig, "04_joint_margin_before_after.png")

    disabled = load(RUNTIME / "round1_disabled/validation_multirate.json")
    final = load(RUNTIME / "nominal_100w0/validation_multirate.json")
    components = sorted(final["rates"]["2000"]["component_min_clearance_m"])
    x = np.arange(len(components))
    width = 0.38
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(x - width / 2, [disabled["rates"]["2000"]["component_min_clearance_m"][c] for c in components], width, label="disabled")
    ax.bar(x + width / 2, [final["rates"]["2000"]["component_min_clearance_m"][c] for c in components], width, label="enabled")
    ax.axhline(.010, color="#c62828", linestyle="--", label="0.010 m gate")
    ax.set_xticks(x, components, rotation=65, ha="right", fontsize=7)
    ax.set(ylabel="minimum clearance (m)", title="Full-body component clearance at 2000 Hz")
    ax.legend()
    save(fig, "05_clearance_before_after.png")

    diag = final["diagnostics"]["records"]
    fig, ax1 = plt.subplots(figsize=(7, 4))
    idx = np.arange(1, len(diag) + 1)
    ax1.plot(idx, [r["barrier_cost"] for r in diag], color="#6a1b9a", label="barrier cost")
    ax1.set(xlabel="diagnostic record", ylabel="barrier cost")
    ax2 = ax1.twinx()
    ax2.plot(idx, [r["min_g"] for r in diag], color="#00838f", label="min g")
    ax2.axhline(0, color="black", linewidth=.7)
    ax2.set_ylabel("min g (m²)")
    ax1.set_title("Execution-envelope optimization diagnostics")
    save(fig, "06_barrier_diagnostics.png")

    labels = list(summary)
    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(labels, [summary[k]["q_min_rad_2000"][1] for k in labels], "o-", label="q2 minimum")
    ax1.axhline(0, color="#c62828", linestyle="--", label="q2 hard floor")
    ax1.set_ylabel("q2 minimum (rad)")
    ax2 = ax1.twinx()
    ax2.plot(labels, [summary[k]["clearance_m_2000"] for k in labels], "s-", color="#2e7d32", label="clearance")
    ax2.set_ylabel("clearance (m)")
    ax1.set_title("Weight candidates")
    save(fig, "07_weight_candidates.png")

    rates = [100, 200, 400, 800, 2000]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(rates, [freq[str(h)]["q_min_rad"][1] for h in rates], "o-", label="q2 minimum")
    ax2 = ax.twinx()
    ax2.plot(rates, [freq[str(h)]["min_full_body_clearance_m"] for h in rates], "s-", color="#2e7d32", label="clearance")
    ax.set(xlabel="validation rate (Hz)", ylabel="q2 minimum (rad)", title="Multirate convergence")
    ax2.set_ylabel("clearance (m)")
    save(fig, "08_frequency_convergence.png")

    nominal = arm("nominal_100w0")
    repeat = arm("nominal_repeat_final_100w0")
    narrow = arm("narrow_final_100w0")

    def animation(path_a: np.ndarray, path_b: np.ndarray, name: str, title: str) -> None:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.set(xlabel="arm x (m)", ylabel="arm z (m)", title=title)
        allp = np.vstack((path_a, path_b))
        ax.set_xlim(float(allp[:, 0].min()) - .002, float(allp[:, 0].max()) + .002)
        ax.set_ylim(float(allp[:, 2].min()) - .002, float(allp[:, 2].max()) + .002)
        line_a, = ax.plot([], [], color="#1565c0", label="nominal")
        line_b, = ax.plot([], [], color="#ef6c00", label="comparison")
        ax.legend()
        frames = np.linspace(1, len(path_a), 24, dtype=int)
        def update(n: int):
            a, b = path_a[:n], path_b[:n]
            line_a.set_data(a[:, 0], a[:, 2])
            line_b.set_data(b[:, 0], b[:, 2])
            return line_a, line_b
        ani = FuncAnimation(fig, update, frames=frames, blit=True)
        ani.save(OUT / name, writer=PillowWriter(fps=8))
        plt.close(fig)

    animation(np.asarray(nominal["position"]), np.asarray(repeat["position"]), "09_nominal_repeat_overlay.gif", "Nominal/repeat overlay")
    animation(np.asarray(nominal["position"]), np.asarray(narrow["position"]), "10_narrow_boundary.gif", "Narrow boundary comparison")
    manifest = {
        "png": sorted(p.name for p in OUT.glob("*.png")),
        "local_animation": sorted(p.name for p in OUT.glob("*.gif")),
        "submission_policy": "PNG and manifest are review artifacts; GIF files remain local and are not submitted.",
    }
    (OUT.parent / "visual_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"png_count": len(manifest["png"]), "gif_count": len(manifest["local_animation"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
