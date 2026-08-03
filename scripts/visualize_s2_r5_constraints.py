"""Create S2-R5 evidence plots and local GIFs from recorded evidence only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from planner_bridge.export.sampling import load_captured_message
from planner_bridge.execution.playback_validator import evaluate_message


EV = ROOT / "docs/evidence/S2-R5"
OUT = EV / "visuals"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(fig, name: str):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=150)
    plt.close(fig)


def violation_series():
    rows = []
    for i in range(4):
        p = EV / "rounds" / f"round_{i}" / "current_q2_violation.json"
        if p.exists():
            d = read(p)
            rows.append((i, d.get("q_min_rad", [np.nan] * 3), d.get("q_max_rad", [np.nan] * 3), d.get("violating_intervals", [])))
        else:
            rows.append((i, [np.nan] * 3, [np.nan] * 3, []))
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = violation_series()
    r4 = read(EV.parent / "S2-R4/root_cause/current_r4_q2_violation.json")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for label, vals, color in [("q1", [x[1][0] for x in rows], "tab:blue"), ("q2", [x[1][1] for x in rows], "tab:red"), ("q3", [x[1][2] for x in rows], "tab:green")]:
        ax.plot(range(4), vals, "o-", label=label, color=color)
    ax.axhline(0, color="black", lw=1)
    ax.set(title="S2-R5 q minima by adaptive round", xlabel="round", ylabel="joint angle (rad)")
    ax.legend()
    save(fig, "01_round_q_minima.png")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    r4_intervals = r4["violating_intervals"]
    for j, item in enumerate(r4_intervals):
        y = 1 + j
        entry_t, min_t, exit_t = item["entry"]["time_s"], item["minimum"]["time_s"], item["exit"]["time_s"]
        ax.plot([entry_t, exit_t], [y, y], lw=8, color="tab:red")
        ax.scatter([min_t], [y], color="black", zorder=3)
        ax.text(entry_t, y + .12, f"R4 interval {j+1}", fontsize=8)
    for i in range(1, 4):
        p = EV / "rounds" / f"round_{i}/current_q2_violation.json"
        if p.exists():
            for item in read(p)["violating_intervals"]:
                ax.axvline(item["entry"]["time_s"], color=f"C{i}", alpha=.35, ls="--")
    ax.set(title="Constraint insertion / violation timeline", xlabel="trajectory time (s)", ylabel="R4 violating interval")
    save(fig, "02_constraint_insertion_timeline.png")

    fig, ax = plt.subplots(figsize=(7, 5))
    arm_path = ROOT / "docs/evidence/S2-R4/runtime/nominal_run_01/trajectory_arm.json"
    if arm_path.exists():
        msg = load_captured_message(arm_path)["message"]
        total = float(np.sum(np.asarray(msg["time"], dtype=float)))
        p = evaluate_message(msg, np.linspace(0.0, total, 800), arm=True)["position"]
        ax.plot(p[:, 0], p[:, 1], color="0.35", lw=1, label="R4 arm polynomial")
        ax.scatter(p[:: max(1, len(p)//40), 0], p[:: max(1, len(p)//40), 1], s=8, color="tab:blue")
    ax.set(title="Arm Cartesian path and sampled envelope view", xlabel="x (m)", ylabel="y (m)")
    ax.legend(loc="best")
    save(fig, "03_arm_path_envelope.png")

    fixed = read(EV / "rounds/round_0/fixed_points.json")
    margins = [x["joint_margin_rad"] for x in fixed["fixed_points"]]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(np.arange(len(margins)), margins, color="tab:green")
    ax.axhline(.02, color="tab:orange", ls="--", label="preferred 0.02")
    ax.axhline(.05, color="tab:red", ls=":", label="robust 0.05")
    ax.set(title="Fixed mode-3 points remain feasible", xlabel="baseline fixed point", ylabel="joint margin (rad)")
    ax.legend()
    save(fig, "04_fixed_points_margin.png")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, (_, qmin, _, _) in enumerate(rows):
        ax.scatter(i, qmin[1], s=70, label=f"R{i}")
    ax.axhline(0, color="black", lw=1)
    ax.axhline(.05, color="tab:orange", ls="--")
    ax.set(title="Fixed-point interpolation overshoot evidence", xlabel="round", ylabel="minimum q2 between fixed points (rad)")
    save(fig, "05_fixed_vs_overshoot.png")

    clearance = []
    for i, run in [(0, "nominal_run_01"), (1, "round_1_nominal_abi_fixed_2"), (2, "round_2_nominal"), (3, "round_3_nominal")]:
        p = EV / "runtime" / run / "numeric_validation.json"
        clearance.append(float(read(p).get("min_full_body_clearance_m", np.nan)) if p.exists() else np.nan)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(range(4), clearance, color="tab:blue")
    ax.axhline(.010, color="tab:red", ls="--", label="hard gate 0.010 m")
    ax.set(title="Full-body clearance by recorded run", xlabel="R4/R5 run", ylabel="minimum clearance (m)")
    ax.legend()
    save(fig, "06_clearance_gate.png")

    for name, title, text in [("07_repeat_status.png", "Nominal repeat", "NOT EXECUTED\nNominal did not pass joint gate"), ("08_narrow_status.png", "Narrow variant", "NOT EXECUTED\nB6 is gated on nominal pass")]:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.text(.5, .5, text, ha="center", va="center", fontsize=16, color="tab:red")
        ax.set(title=title, xticks=[], yticks=[])
        save(fig, name)

    frames = []
    for i, (_, qmin, _, _) in enumerate(rows):
        img = Image.new("RGB", (640, 360), "white")
        draw = ImageDraw.Draw(img)
        draw.text((30, 30), f"S2-R5 Round {i}", fill="black")
        draw.text((30, 90), f"q1 min = {qmin[0]:.6f} rad", fill="black")
        draw.text((30, 130), f"q2 min = {qmin[1]:.6f} rad", fill="red")
        draw.text((30, 170), f"q3 min = {qmin[2]:.6f} rad", fill="black")
        draw.text((30, 250), "Recorded evidence; no clipping or projection", fill="black")
        frames.append(img)
    frames[0].save(OUT / "09_round_q2_evolution.gif", save_all=True, append_images=frames[1:], duration=700, loop=0)

    arm_frames = []
    arm_path = ROOT / "docs/evidence/S2-R4/runtime/nominal_run_01/trajectory_arm.json"
    if arm_path.exists():
        msg = load_captured_message(arm_path)["message"]
        total = float(np.sum(np.asarray(msg["time"], dtype=float)))
        path = evaluate_message(msg, np.linspace(0.0, total, 800), arm=True)["position"]
        for end in np.linspace(max(2, len(path) // 8), len(path), 8, dtype=int):
            img = Image.new("RGB", (640, 360), "white")
            draw = ImageDraw.Draw(img)
            xs, ys = path[:end, 0], path[:end, 1]
            lo_x, hi_x = float(xs.min()), float(xs.max())
            lo_y, hi_y = float(ys.min()), float(ys.max())
            sx = 560.0 / max(hi_x - lo_x, 1e-9)
            sy = 280.0 / max(hi_y - lo_y, 1e-9)
            pts = [(40 + (x - lo_x) * sx, 310 - (y - lo_y) * sy) for x, y in zip(xs, ys)]
            if len(pts) > 1:
                draw.line(pts, fill="blue", width=2)
            draw.text((30, 20), "Recorded R4 arm path progression", fill="black")
            arm_frames.append(img)
    if arm_frames:
        arm_frames[0].save(OUT / "10_arm_path_evolution.gif", save_all=True, append_images=arm_frames[1:], duration=350, loop=0)

    manifest = {
        "png": [f"{i:02d}_{name}" for i, name in enumerate(["round_q_minima.png", "constraint_insertion_timeline.png", "arm_path_envelope.png", "fixed_points_margin.png", "fixed_vs_overshoot.png", "clearance_gate.png", "repeat_status.png", "narrow_status.png"], start=1)],
        "local_gif": ["09_round_q2_evolution.gif", "10_arm_path_evolution.gif"],
        "source": "recorded S2-R4/R5 evidence; missing B6 variants are explicitly marked NOT EXECUTED",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
