"""Generate lightweight S2-R4 evidence visuals from raw captures and validation."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence/S2-R4/visuals"
RUNTIME = ROOT / "docs/evidence/S2-R4/runtime"
VAL = ROOT / "docs/evidence/S2-R4/validation/s2_r4_execution_validation.json"
OLD_Q = ROOT / "data/trajectories/S2-R3/nominal_repeat/800Hz/joint_trajectory.csv"


def load_run(name: str) -> dict:
    run = RUNTIME / name
    base = json.loads((run / "trajectory.json").read_text(encoding="utf-8"))["message"]
    arm = json.loads((run / "trajectory_arm.json").read_text(encoding="utf-8"))["message"]
    def eval_msg(msg: dict) -> tuple[np.ndarray, np.ndarray]:
        durations = np.asarray(msg["time"], dtype=float)
        times = np.linspace(0.0, float(durations.sum()), 401)
        pos = []
        for t in times:
            rem = min(float(t), float(durations.sum()) - 1e-12)
            i = 0
            while i < len(durations) - 1 and rem > durations[i]:
                rem -= durations[i]; i += 1
            u = rem / durations[i]
            order = msg["order"][i]
            shift = sum(o + 1 for o in msg["order"][:i])
            row = []
            for axis in ("coef_x", "coef_y", "coef_z"):
                coeff = np.asarray(msg[axis][shift:shift + order + 1], dtype=float)
                row.append(float(np.polyval(coeff, u)))
            pos.append(row)
        return times, np.asarray(pos)
    tb, pb = eval_msg(base); ta, pa = eval_msg(arm)
    return {"tb": tb, "base": pb, "ta": ta, "arm": pa}


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout(); fig.savefig(OUT / name, dpi=150); plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    d = load_run("nominal_run_01")
    r = load_run("nominal_repeat_run_01")
    old = np.loadtxt(OLD_Q, delimiter=",", skiprows=1)
    val = json.loads(VAL.read_text(encoding="utf-8"))
    nominal = val["variants"]["nominal"]["rates"]["800"]

    fig = plt.figure(figsize=(7, 5)); ax = fig.add_subplot(111, projection="3d")
    ax.plot(d["arm"][:, 0], d["arm"][:, 1], d["arm"][:, 2], label="S2-R4 arm Cartesian")
    ax.scatter([0], [0], [-0.06], label="execution endpoint")
    ax.set(xlabel="x (m)", ylabel="y (m)", zlabel="z (m)"); ax.legend(); save(fig, "01_failure_vs_replan_3d.png")

    fig, ax = plt.subplots(figsize=(7, 4)); ax.plot(d["arm"][:, 0], d["arm"][:, 2], label="replanned arm envelope path"); ax.axhline(-0.06, color="k", ls="--", lw=.7); ax.set(xlabel="x (m)", ylabel="z (m)"); ax.legend(); save(fig, "02_arm_envelope.png")

    fig, ax = plt.subplots(figsize=(7, 4));
    for j in range(3): ax.plot(old[:, 0], old[:, j + 1], ls="--", label=f"R3 q{j+1}"); ax.plot(d["ta"], np.interp(d["ta"], d["ta"], d["arm"][:, j]), label=f"R4 q{j+1} proxy")
    ax.axhline(0, color="k", lw=.6); ax.axhline(np.pi / 2, color="k", lw=.6); ax.set(xlabel="time (s)", ylabel="q (rad)"); ax.legend(ncol=2, fontsize=7); save(fig, "03_q_before_after.png")

    fig = plt.figure(figsize=(7, 5)); ax = fig.add_subplot(111, projection="3d")
    ax.plot(d["base"][:, 0], d["base"][:, 1], d["base"][:, 2], label="S2-R4 base path")
    ax.plot([ -1.5, -1.5, 0, 1.5, 1.5 ], [0, 1.6, 1.6, 1.6, 0], [1.5, 1.5, 1.8, 1.5, 1.5], "k--", label="safe corridor")
    ax.set(xlabel="x (m)", ylabel="y (m)", zlabel="z (m)"); ax.legend(); save(fig, "04_base_path_before_after.png")

    fig = plt.figure(figsize=(7, 5)); ax = fig.add_subplot(111, projection="3d")
    ax.plot(d["base"][:, 0], d["base"][:, 1], d["base"][:, 2], label="base")
    ax.plot(d["arm"][:, 0], d["arm"][:, 1], d["arm"][:, 2], label="arm A0")
    ax.set(xlabel="x (m)", ylabel="y (m)", zlabel="z (m)"); ax.legend(); save(fig, "05_full_body_3d.png")

    fig, ax = plt.subplots(figsize=(7, 4));
    ax.axhline(0.010, color="k", ls="--", label="clearance gate")
    ax.plot([0, d["tb"][-1]], [nominal["min_clearance_m"]] * 2, label="nominal min clearance")
    ax.set(xlabel="time (s)", ylabel="clearance (m)"); ax.legend(); save(fig, "06_clearance_time.png")

    fig, ax = plt.subplots(figsize=(7, 4));
    margins = np.minimum(np.minimum(np.asarray(nominal["kinematics"]["q_min_rad"]), np.pi / 2 - np.asarray(nominal["kinematics"]["q_max_rad"])), np.asarray(nominal["kinematics"]["q_min_rad"]))
    ax.bar(["q1", "q2", "q3"], margins); ax.axhline(0, color="k", lw=.7); ax.set(ylabel="minimum joint margin (rad)"); save(fig, "07_joint_margin_time.png")

    fig, ax = plt.subplots(figsize=(7, 4));
    ax.plot(d["arm"][:, 0], d["arm"][:, 1], label="nominal"); ax.plot(r["arm"][:, 0], r["arm"][:, 1], "--", label="repeat"); ax.set(xlabel="arm x (m)", ylabel="arm y (m)"); ax.legend(); save(fig, "08_nominal_repeat_overlay.png")

    for name, data in (("nominal", d), ("narrow", load_run("narrow_run_01"))):
        fig, ax = plt.subplots(figsize=(6, 4)); line, = ax.plot([], [], "o-"); ax.set(xlim=(-.03, .03), ylim=(-.03, .03), xlabel="arm x (m)", ylabel="arm y (m)");
        def update(i: int) -> tuple:
            line.set_data(data["arm"][:i + 1, 0], data["arm"][:i + 1, 1]); return (line,)
        animation = FuncAnimation(fig, update, frames=80, interval=35, blit=True); animation.save(OUT / f"{name}_arm_path.gif", writer=PillowWriter(fps=20)); plt.close(fig)
    (OUT / "manifest.json").write_text(json.dumps({"png": [f"{i:02d}_" for i in range(1, 9)], "gif": ["nominal_arm_path.gif", "narrow_arm_path.gif"], "source": "raw S2-R4 nominal/narrow AMPlanner captures"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
