"""Run a bounded Isaac Sim reference-state playback over the S3 trajectory."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import numpy as np
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
    parser.add_argument("--disable-joint-physics", action="store_true")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo))
    from planner_bridge.execution.official_delta_kinematics import official_fk_joint_state

    trajectory = json.loads(Path(args.trajectory).read_text(encoding="utf-8"))
    frames = trajectory["frames"]
    app = SimulationApp({"headless": True, "hide_ui": True})
    try:
        import omni.timeline
        import omni.usd
        import carb
        import omni.physx
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

        scene_boxes = {
            "/World/Crossarm/MainBeam": ([0.15, 0.0, -0.34], [0.70, 0.10, 0.08]),
            "/World/Crossarm/Column": ([0.0, 0.0, -0.095], [0.12, 0.12, 0.49]),
            "/World/Crossarm/AdjacentObstacle": ([0.12, 0.28, -0.22], [0.12, 0.10, 0.30]),
            "/World/TargetProxy": ([0.0, 0.0, -0.25025], [0.06, 0.06, 0.06]),
        }
        scene_query = omni.physx.get_physx_scene_query_interface()

        def overlap_paths(center: list[float], size: list[float]) -> list[str]:
            hits: list[str] = []

            def on_hit(hit):
                hits.append(str(hit.rigid_body))
                return True

            scene_query.overlap_box(
                carb.Float3(size[0] * 0.5, size[1] * 0.5, size[2] * 0.5),
                carb.Float3(*center),
                carb.Float4(0.0, 0.0, 0.0, 1.0),
                on_hit,
                False,
            )
            return sorted(set(hits))

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
        if args.disable_joint_physics:
            for prim in joint_prims.values():
                prim.GetAttribute("physics:jointEnabled").Set(False)
            print("PLAYBACK_JOINT_PHYSICS_DISABLED", flush=True)
        print("PLAYBACK_JOINTS_READY", flush=True)

        timeline = omni.timeline.get_timeline_interface()
        timeline.play()
        max_fk_error = 0.0
        max_world_error = 0.0
        max_joint_error = 0.0
        max_raw_joint_error = 0.0
        max_joint_error_next_frame = 0.0
        max_joint_abs_error_by_joint = [0.0, 0.0, 0.0]
        first_joint_probe = None
        last_joint_probe = None
        contact_hits: list[dict[str, object]] = []
        clearance_expanded_hits: list[dict[str, object]] = []
        finite = True
        observed_physics_steps = 0
        phase_ids = []
        for frame_index, frame in enumerate(frames):
            q = frame["q_rad"]
            qdot = frame["qdot_rad_s"]
            written_q = [float(np.float32(value)) for value in q]
            written_qdot = [float(np.float32(value)) for value in qdot]
            robot_translate.Set(Gf.Vec3d(*frame["base_position_m"]))
            for name, value, velocity in zip(active, written_q, written_qdot):
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
            for obstacle_path, (center, size) in scene_boxes.items():
                for hit in overlap_paths(center, size):
                    if hit not in scene_boxes:
                        if len(contact_hits) < 100:
                            contact_hits.append({"frame": frame_index, "obstacle": obstacle_path, "hit": hit})
                expanded = [float(value) + 0.02 for value in size]
                for hit in overlap_paths(center, expanded):
                    if hit not in scene_boxes:
                        if len(clearance_expanded_hits) < 100:
                            clearance_expanded_hits.append({"frame": frame_index, "obstacle": obstacle_path, "hit": hit})
            readback = []
            for name in active:
                value = joint_prims[name].GetAttribute("state:angular:physics:position").Get()
                readback.append(float(value) if value is not None else float("nan"))
            signed_error = [float(a - b) for a, b in zip(readback, written_q)]
            raw_signed_error = [float(a - b) for a, b in zip(readback, q)]
            if first_joint_probe is None:
                first_joint_probe = {"raw_target": [float(v) for v in q], "written_float32": written_q, "readback": readback, "signed_error": signed_error, "raw_signed_error": raw_signed_error}
            last_joint_probe = {"raw_target": [float(v) for v in q], "written_float32": written_q, "readback": readback, "signed_error": signed_error, "raw_signed_error": raw_signed_error}
            max_joint_error = max(max_joint_error, max(abs(value) for value in signed_error))
            max_raw_joint_error = max(max_raw_joint_error, max(abs(value) for value in raw_signed_error))
            next_q = frames[frame_index + 1]["q_rad"] if frame_index + 1 < len(frames) else q
            max_joint_error_next_frame = max(
                max_joint_error_next_frame,
                max(abs(float(a) - float(b)) for a, b in zip(readback, next_q)),
            )
            max_joint_abs_error_by_joint = [
                max(previous, abs(current)) for previous, current in zip(max_joint_abs_error_by_joint, signed_error)
            ]
            # S3 protocol q_rad uses the endCallback joint-state convention;
            # convert it through the project's official joint-state FK.
            fk = official_fk_joint_state(q)
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
            "max_raw_reference_to_joint_readback_error_rad": max_raw_joint_error,
            "joint_state_storage_dtype": "float32 USD PhysicsJointStateAPI attribute",
            "max_joint_readback_error_to_next_reference_rad": max_joint_error_next_frame,
            "max_joint_abs_error_by_active_joint_rad": max_joint_abs_error_by_joint,
            "first_joint_probe": first_joint_probe,
            "last_joint_probe": last_joint_probe,
            "max_arm_fk_error_m": max_fk_error,
            "max_world_ee_error_m": max_world_error,
            "required_prim_paths": [
                "/World/Robot",
                "/World/Crossarm/MainBeam",
                "/World/Crossarm/Column",
                "/World/Crossarm/AdjacentObstacle",
                "/World/TargetProxy",
            ],
            "contact_query_hits": contact_hits,
            "clearance_expanded_query_hits": clearance_expanded_hits,
            "contact_query": "PASS" if not contact_hits else "FAIL",
            "penetration_m": 0.0 if not contact_hits else None,
            "clearance_gate": "PASS_LOWER_BOUND_0.010M" if not clearance_expanded_hits else "FAIL",
            "min_clearance_m": None,
            "clearance_lower_bound_m": 0.010 if not clearance_expanded_hits else None,
            "s2_clearance_delta_m": None,
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
