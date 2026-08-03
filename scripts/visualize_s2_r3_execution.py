from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from planner_bridge.execution.full_body_proxy import ROTOR_CENTERS_B, T_B_A0
from planner_bridge.execution.official_delta_kinematics import official_joint_points
from planner_bridge.execution.playback_validator import sample_raw
from planner_bridge.execution.official_flatness_wrapper import quaternion_to_rotation_wxyz


OUT = ROOT / "docs" / "evidence" / "S2-R3" / "visuals"


def _load(variant: str):
    base = sample_raw(ROOT / "data/trajectories/S2-R2/100Hz" / variant / "raw_trajectory.json", 800)
    arm = sample_raw(ROOT / "data/trajectories/S2-R2/100Hz" / variant / "raw_trajectory_arm.json", 800, arm=True)
    q = np.load(ROOT / "data/trajectories/S2-R3" / variant / "800Hz" / "joint_trajectory.npz")["q"]
    attitude = json.loads((ROOT / "docs/evidence/S2-R3/attitude" / variant / "800Hz.json").read_text(encoding="utf-8"))
    return base, arm, q, attitude


def _save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=140)
    plt.close(fig)


def _frame_points(base, arm, q, index):
    R = quaternion_to_rotation_wxyz(np.asarray(json.loads((ROOT / "docs/evidence/S2-R3/attitude/nominal/800Hz.json").read_text()) if False else [1, 0, 0, 0]))
    # Recompute the frame quaternion through the same wrapper contract.
    from planner_bridge.execution.official_flatness_wrapper import OfficialFlatnessMap
    flat = OfficialFlatnessMap()
    _, quat, _ = flat.forward(base["velocity"][index], base["acceleration"][index], base["jerk"][index], 0.0, 0.01)
    R = quaternion_to_rotation_wxyz(quat)
    p_wb = base["position"][index]
    arm_point = arm["position"][index]
    qv = q[index]
    jp = official_joint_points(arm_point, qv)
    def world_a0(points):
        b = (T_B_A0[:3, :3] @ np.asarray(points).T).T + T_B_A0[:3, 3]
        return p_wb + (R @ b.T).T
    return p_wb, R, world_a0(jp["A"]), world_a0(jp["B"]), world_a0(jp["C"]), world_a0(jp["B_left"]), world_a0(jp["B_right"]), world_a0(jp["C_left"]), world_a0(jp["C_right"])


def main() -> int:
    base, arm, q, attitude = _load("nominal")
    t = base["time"]
    ee = []
    for i in range(len(t)):
        _, R, *_ = _frame_points(base, arm, q, i)
        b = (T_B_A0[:3, :3] @ arm["position"][i]) + T_B_A0[:3, 3]
        ee.append(base["position"][i] + R @ b)
    ee = np.asarray(ee)

    fig = plt.figure(figsize=(8, 6)); ax = fig.add_subplot(111, projection="3d")
    ax.plot(base["position"][:, 0], base["position"][:, 1], base["position"][:, 2], label="body")
    ax.plot(ee[:, 0], ee[:, 1], ee[:, 2], label="end-effector")
    ax.set_title("S2-R3 nominal whole trajectory"); ax.set_xlabel("x W (m)"); ax.set_ylabel("y W (m)"); ax.set_zlabel("z W (m)"); ax.legend(); _save(fig, "01_nominal_whole_trajectory_3d.png")

    fig, ax = plt.subplots(figsize=(9, 4)); ax.plot(t, q); ax.set_title("Official IK joint trajectory"); ax.set_xlabel("time (s)"); ax.set_ylabel("q (rad)"); ax.axhline(0, color="k", lw=.7); ax.axhline(np.pi/2, color="k", lw=.7); ax.legend(["m1_1", "m2_1", "m3_1"]); _save(fig, "02_joint_limits_and_trajectory.png")

    fig = plt.figure(figsize=(8, 6)); ax = fig.add_subplot(111, projection="3d")
    for i in range(0, len(t), max(1, len(t)//80)):
        p, R, *_ = _frame_points(base, arm, q, i)
        rotor = p + (R @ ROTOR_CENTERS_B.T).T
        ax.scatter(rotor[:, 0], rotor[:, 1], rotor[:, 2], s=4, c="tab:red")
    ax.plot(base["position"][:, 0], base["position"][:, 1], base["position"][:, 2], c="tab:blue")
    ax.set_title("Rotor-center sweep (disk radius 0.25 m proxy)"); ax.set_xlabel("x W (m)"); ax.set_ylabel("y W (m)"); ax.set_zlabel("z W (m)"); _save(fig, "03_rotor_sweep_3d.png")

    fig, ax = plt.subplots(figsize=(8, 4)); rates = [100, 200, 400, 800]
    mins = []
    for rate in rates:
        d = json.loads((ROOT / "docs/evidence/S2-R3/collision/nominal" / f"{rate}Hz.json").read_text(encoding="utf-8")); mins.append(d["component_clearance_m"][d["most_dangerous_component"]])
    ax.plot(rates, mins, "o-"); ax.axhline(.01, color="tab:red", ls="--", label="0.010 m gate"); ax.set_title("Nominal whole-body proxy clearance vs frequency"); ax.set_xlabel("sampling rate (Hz)"); ax.set_ylabel("minimum clearance (m)"); ax.legend(); _save(fig, "04_clearance_frequency_convergence.png")

    fig, ax = plt.subplots(figsize=(9, 4)); flat = __import__("planner_bridge.execution.official_flatness_wrapper", fromlist=["OfficialFlatnessMap"]).OfficialFlatnessMap(); roll=[]; pitch=[]
    for i in range(len(t)):
        _, quat, _ = flat.forward(base["velocity"][i], base["acceleration"][i], base["jerk"][i], 0., .01); R = quaternion_to_rotation_wxyz(quat); roll.append(np.arctan2(R[2,1], R[2,2])); pitch.append(np.arcsin(-R[2,0]))
    ax.plot(t, roll, label="roll"); ax.plot(t, pitch, label="pitch"); ax.set_title("Official FlatnessMap attitude"); ax.set_xlabel("time (s)"); ax.set_ylabel("angle (rad)"); ax.legend(); _save(fig, "05_flatness_attitude_roll_pitch.png")

    fig, ax = plt.subplots(figsize=(8, 4)); ax.plot(t, attitude.get("thrust_min_N", np.zeros(len(t))) * np.ones(len(t)), alpha=0); ax.axhline(0, color="k", lw=.7); ax.bar(["min thrust", "max thrust", "max omega"], [attitude["thrust_min_N"], attitude["thrust_max_N"], attitude["omega_max_rad_s"]]); ax.set_title("FlatnessMap finite/thrust/omega summary"); _save(fig, "06_attitude_finiteness_summary.png")

    index = int(np.argmin([json.loads((ROOT / "docs/evidence/S2-R3/collision/nominal" / "800Hz.json").read_text())["component_clearance_m"]["body"]])) if False else int(np.argmin(np.linalg.norm(base["position"] - np.mean(base["position"], axis=0), axis=1)))
    p, R, A, B, C, Bl, Br, Cl, Cr = _frame_points(base, arm, q, index)
    fig = plt.figure(figsize=(8, 6)); ax = fig.add_subplot(111, projection="3d")
    for i in range(3):
        ax.plot([A[i,0], B[i,0]], [A[i,1], B[i,1]], [A[i,2], B[i,2]], c="tab:orange")
        ax.plot([Bl[i,0], Cl[i,0]], [Bl[i,1], Cl[i,1]], [Bl[i,2], Cl[i,2]], c="tab:green")
        ax.plot([Br[i,0], Cr[i,0]], [Br[i,1], Cr[i,1]], [Br[i,2], Cr[i,2]], c="tab:green")
    ax.scatter(*p, c="tab:red"); ax.set_title("Official joint points and capsules"); ax.set_xlabel("x W (m)"); ax.set_ylabel("y W (m)"); ax.set_zlabel("z W (m)"); _save(fig, "07_joint_points_capsules_snapshot.png")

    repeat = np.load(ROOT / "data/trajectories/S2-R3/nominal_repeat/800Hz/joint_trajectory.npz")["q"]
    fig, ax = plt.subplots(figsize=(9, 4)); ax.plot(t, q, lw=1); ax.plot(t, repeat, ls="--", lw=.6); ax.set_title("Nominal/repeat joint overlay (solid/dashed)"); ax.set_xlabel("time (s)"); ax.set_ylabel("q (rad)"); _save(fig, "08_nominal_repeat_joint_overlay.png")

    def make_gif(path: Path, arm_mode: bool) -> None:
        fig = plt.figure(figsize=(6, 5)); ax = fig.add_subplot(111, projection="3d")
        indices = np.linspace(0, len(t)-1, 24, dtype=int)
        def update(i):
            ax.clear(); j = indices[i]; p, R, A, B, C, Bl, Br, Cl, Cr = _frame_points(base, arm, q, j)
            ax.plot(base["position"][:j+1,0], base["position"][:j+1,1], base["position"][:j+1,2], c="tab:blue")
            if arm_mode:
                for k in range(3):
                    ax.plot([A[k,0],B[k,0]],[A[k,1],B[k,1]],[A[k,2],B[k,2]], c="tab:orange")
                    ax.plot([Bl[k,0],Cl[k,0]],[Bl[k,1],Cl[k,1]],[Bl[k,2],Cl[k,2]], c="tab:green")
                    ax.plot([Br[k,0],Cr[k,0]],[Br[k,1],Cr[k,1]],[Br[k,2],Cr[k,2]], c="tab:green")
            ax.set_title(f"S2-R3 nominal t={t[j]:.2f}s"); ax.set_xlim(-.5,.5); ax.set_ylim(-.5,.5); ax.set_zlim(.2,1.8)
        anim = FuncAnimation(fig, update, frames=len(indices), interval=80); anim.save(path, writer=PillowWriter(fps=12)); plt.close(fig)
    make_gif(OUT / "09_nominal_body_animation.gif", False)
    make_gif(OUT / "10_nominal_arm_capsule_animation.gif", True)
    manifest = {"png": [f"0{i}_{name}.png" for i, name in enumerate(["nominal_whole_trajectory_3d", "joint_limits_and_trajectory", "rotor_sweep_3d", "clearance_frequency_convergence", "flatness_attitude_roll_pitch", "attitude_finiteness_summary", "joint_points_capsules_snapshot", "nominal_repeat_joint_overlay"], 1)], "local_video": ["09_nominal_body_animation.gif", "10_nominal_arm_capsule_animation.gif"], "video_committed": False}
    (OUT / "visual_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
