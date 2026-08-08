"""Capture the missing floating-base pose channels for the R6 state audit.

The R5 raw traces already contain q, dq, qdd and base velocities.  This
read-only supplemental capture uses the same authored USD, solver settings,
initial state and effort path, adding only PhysX readback position and
orientation to the q1 trace.
"""

from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path

import numpy as np

import s4_r6_r5_corrected_convergence_freeze as r5

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "docs/evidence/S4-R6-R6/diagnosis"
RATES = (240, 480, 960, 1920)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def base_pose(base):
    positions, orientations = base.get_world_poses()
    return (
        np.asarray(positions, dtype=float).reshape(-1, 3)[0].tolist(),
        np.asarray(orientations, dtype=float).reshape(-1, 4)[0].tolist(),
    )


def capture(rate: int, output: Path) -> int:
    from isaacsim import SimulationApp

    app = None
    try:
        app = SimulationApp({"headless": True, "hide_ui": True, "disable_viewport_updates": True, "renderer": "MinimalRendering"})
        _, world, art, _, base = r5.create_simulation(r5.ASSET, 1.0 / rate)
        r5.configure(art, world, [0.0, 0.0, 0.0, 0.0])
        zero = {"q1": 0.0, "q2": 0.0, "q3": 0.0, "d": 0.0}
        for _ in range(2):
            art.apply_action(r5.effort_action(art, zero))
            world.step(render=False)
        dt = 1.0 / rate
        steps = int(round(r5.TOTAL_DURATION_S / dt))
        q0 = r5.native_to_canonical(art, art.get_joint_positions())
        dq0 = r5.native_to_canonical(art, art.get_joint_velocities())
        pos0, ori0 = base_pose(base)
        previous_dq = dq0.copy()
        records = [{
            "step": 0, "time_s": 0.0, "q": q0, "dq": dq0,
            "qdd": {name: 0.0 for name in q0},
            "base_position_world_m": pos0,
            "base_orientation_world_wxyz": ori0,
            "base_linear_velocity_m_s": np.asarray(base.get_linear_velocities(), dtype=float).reshape(-1).tolist(),
            "base_angular_velocity_rad_s": np.asarray(base.get_angular_velocities(), dtype=float).reshape(-1).tolist(),
        }]
        for step in range(1, steps + 1):
            active = ((step - 1) * dt) < r5.PULSE_DURATION_S - 1.0e-14
            command = {"q1": r5.Q1_EFFORT_NM if active else 0.0, "q2": 0.0, "q3": 0.0, "d": 0.0}
            art.apply_action(r5.effort_action(art, command))
            world.step(render=False)
            q = r5.native_to_canonical(art, art.get_joint_positions())
            dq = r5.native_to_canonical(art, art.get_joint_velocities())
            pos, ori = base_pose(base)
            qdd = {name: float((dq[name] - previous_dq[name]) / dt) for name in q}
            records.append({
                "step": step, "time_s": step * dt, "q": q, "dq": dq, "qdd": qdd,
                "base_position_world_m": pos, "base_orientation_world_wxyz": ori,
                "base_linear_velocity_m_s": np.asarray(base.get_linear_velocities(), dtype=float).reshape(-1).tolist(),
                "base_angular_velocity_rad_s": np.asarray(base.get_angular_velocities(), dtype=float).reshape(-1).tolist(),
            })
            previous_dq = dq
        write_json(output, {
            "task": "S4-R6-R6-CONVERGENCE-METRIC-AUDIT-AND-FREEZE-R1",
            "rate_hz": rate, "dt_s": dt, "total_duration_s": r5.TOTAL_DURATION_S,
            "pulse_duration_s": r5.PULSE_DURATION_S,
            "source": "same R5 native floating RRRP runtime protocol; supplemental PhysX base pose readback",
            "records": records,
            "finite": all(r5.finite(row[key]) for row in records for key in ("q", "dq", "qdd", "base_position_world_m", "base_orientation_world_wxyz", "base_linear_velocity_m_s", "base_angular_velocity_rad_s")),
        })
        return 0
    except BaseException:
        write_json(output, {"task": "S4-R6-R6-CONVERGENCE-METRIC-AUDIT-AND-FREEZE-R1", "rate_hz": rate, "finite": False, "error": traceback.format_exc()})
        return 1
    finally:
        if app is not None:
            app.close(wait_for_replicator=False, skip_cleanup=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate", type=int, choices=RATES, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    raise SystemExit(capture(args.rate, args.output or OUTPUT_ROOT / f"state_rate_{args.rate}hz.json"))
