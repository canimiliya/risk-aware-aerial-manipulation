"""Run a bounded Isaac Sim reference-state playback over the S3 trajectory."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from isaacsim import SimulationApp


def _await_stage(app, context):
    future = asyncio.ensure_future(context.new_stage_async())
    while not future.done():
        app.update()
    return context.get_stage()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--robot-usd", required=True)
    parser.add_argument("--trajectory", required=True)
    parser.add_argument("--scene-usd", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo))
    from planner_bridge.execution.official_delta_kinematics import official_fk

    trajectory = json.loads(Path(args.trajectory).read_text(encoding="utf-8"))
    frames = trajectory["frames"]
    app = SimulationApp({"headless": True, "hide_ui": True})
    try:
        import omni.timeline
        import omni.usd
        from pxr import Gf, Sdf, UsdGeom, UsdPhysics

        stage = _await_stage(app, omni.usd.get_context())
        world_prim = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world_prim)
        stage.DefinePrim("/World/PhysicsScene", "PhysicsScene")
        print("PLAYBACK_STAGE_READY", flush=True)

        robot = stage.DefinePrim("/World/Robot", "Xform")
        robot.GetReferences().AddReference(str(Path(args.robot_usd).resolve()))
        robot_xform = UsdGeom.Xformable(robot)
        robot_translate = robot_xform.AddTranslateOp()

        def cube(path: str, center: list[float], size: list[float], label: str):
            prim = stage.DefinePrim(path, "Cube")
            cube = UsdGeom.Cube(prim)
            cube.CreateSizeAttr(1.0)
            UsdGeom.Xformable(prim).AddTranslateOp().Set(Gf.Vec3d(*center))
            UsdGeom.Xformable(prim).AddScaleOp().Set(Gf.Vec3f(*size))
            UsdPhysics.CollisionAPI.Apply(prim)
            prim.SetCustomDataByKey("s3_label", label)

        # Reuse the frozen nominal S2 proxy contract; it remains explicitly provisional.
        cube("/World/Crossarm/MainBeam", [0.15, 0.0, -0.34], [0.70, 0.10, 0.08], "main_crossarm_provisional")
        cube("/World/Crossarm/Column", [0.0, 0.0, -0.095], [0.12, 0.12, 0.49], "support_column_provisional")
        cube("/World/Crossarm/AdjacentObstacle", [0.12, 0.28, -0.22], [0.12, 0.10, 0.30], "adjacent_obstacle_provisional")
        cube("/World/TargetProxy", [0.0, 0.0, -0.25025], [0.06, 0.06, 0.06], "target_proxy_provisional")

        for _ in range(40):
            app.update()
        print("PLAYBACK_REFERENCES_READY", flush=True)

        active = ["m1_1", "m2_1", "m3_1"]
        joint_prims = {}
        for name in active:
            candidates = [
                prim for prim in stage.Traverse() if str(prim.GetPath()).endswith(f"/joints/{name}")
            ]
            joint_prims[name] = candidates[0] if candidates else stage.GetPrimAtPath("/Missing")
        missing = [name for name, prim in joint_prims.items() if not prim.IsValid()]
        if missing:
            raise RuntimeError(f"active joint prims missing: {missing}")
        print("PLAYBACK_JOINTS_READY", flush=True)

        timeline = omni.timeline.get_timeline_interface()
        timeline.play()
        max_fk_error = 0.0
        max_world_error = 0.0
        max_joint_error = 0.0
        finite = True
        observed_physics_steps = 0
        phase_ids = []
        for frame in frames:
            q = frame["q_rad"]
            qdot = frame["qdot_rad_s"]
            robot_translate.Set(Gf.Vec3d(*frame["base_position_m"]))
            for name, value, velocity in zip(active, q, qdot):
                prim = joint_prims[name]
                prim.GetAttribute("drive:angular:physics:targetPosition").Set(float(value))
                prim.GetAttribute("drive:angular:physics:targetVelocity").Set(float(velocity))
                state = prim.GetAttribute("state:angular:physics:position")
                if state.IsValid():
                    state.Set(float(value))
                state_velocity = prim.GetAttribute("state:angular:physics:velocity")
                if state_velocity.IsValid():
                    state_velocity.Set(float(velocity))
            app.update()
            observed_physics_steps += 1
            readback = []
            for name in active:
                value = joint_prims[name].GetAttribute("state:angular:physics:position").Get()
                readback.append(float(value) if value is not None else float("nan"))
            max_joint_error = max(max_joint_error, max(abs(a - b) for a, b in zip(readback, q)))
            fk = official_fk(q)
            arm = frame["arm_cartesian_position_m"]
            world = frame["world_ee_position_m"]
            world_fk = [frame["base_position_m"][i] + float(fk[i]) for i in range(3)]
            max_fk_error = max(max_fk_error, max(abs(float(fk[i]) - arm[i]) for i in range(3)))
            max_world_error = max(max_world_error, max(abs(world_fk[i] - world[i]) for i in range(3)))
            phase_ids.append(frame["phase_id"])
            finite = finite and all(abs(float(value)) < float("inf") for value in q + qdot + list(fk) + world_fk)
        timeline.stop()
        stage.GetRootLayer().Export(args.scene_usd)

        result = {
            "mode": "REFERENCE_STATE_PLAYBACK",
            "variant": trajectory["variant"],
            "frames": len(frames),
            "duration_s": frames[-1]["time"],
            "physics_dt_s": 1.0 / 240.0,
            "rendering_dt_s": 1.0 / 60.0,
            "num_envs": 1,
            "observed_physics_steps": observed_physics_steps,
            "monotonic_time": all(a["time"] < b["time"] for a, b in zip(frames, frames[1:])),
            "finite": finite,
            "active_joints": active,
            "passive_joints": ["m1_2", "m1_3", "m2_2", "m2_3", "m3_2", "m3_3"],
            "max_joint_state_write_readback_error_rad": max_joint_error,
            "max_arm_fk_error_m": max_fk_error,
            "max_world_ee_error_m": max_world_error,
            "required_prim_paths": [
                "/World/Robot",
                "/World/Crossarm/MainBeam",
                "/World/Crossarm/Column",
                "/World/Crossarm/AdjacentObstacle",
                "/World/TargetProxy",
            ],
            "contact_query": "NOT_IMPLEMENTED_IN_REFERENCE_STATE_PLAYBACK",
            "clearance_gate": "NOT_EXECUTED",
            "closed_loop": False,
        }
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("ISAAC_PLAYBACK_RESULT", result, flush=True)
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
