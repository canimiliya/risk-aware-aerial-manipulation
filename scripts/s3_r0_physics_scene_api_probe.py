"""Probe the Isaac Lab PhysicsScene API used by the S3-R0 playback.

This is intentionally a small real-application probe.  It verifies the
schema ownership of the timestep attribute and that SimulationCfg is the
single source of physics dt, gravity, and scene-query configuration.
"""

from __future__ import annotations

import asyncio
import json
import traceback
from pathlib import Path


PHYSICS_DT_S = 1.0 / 240.0
OUTPUT = Path("docs/evidence/S3-R0/physics_scene_api_probe.json")


def _write(payload: dict[str, object]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_name(f".{OUTPUT.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)


def _new_stage(app: object, context: object) -> object:
    future = asyncio.ensure_future(context.new_stage_async())
    for _ in range(480):
        if future.done():
            return context.get_stage()
        app.update()
    raise TimeoutError("new_stage_async did not complete within 480 app updates")


def main() -> int:
    result: dict[str, object] = {
        "decision": "BLOCKED_S3_R0_R5_PHYSICS_SETUP",
        "simulation_cfg_dt_s": PHYSICS_DT_S,
        "usdphysics_scene_has_timestep_creator": False,
        "physx_scene_api_has_timestep_creator": False,
        "physics_scene_exists": False,
        "physics_dt_s": None,
        "physics_scene_time_steps_per_second": None,
        "scene_query_enabled": None,
        "gravity_xyz": None,
        "error": None,
    }
    app = None
    sim = None
    try:
        from isaacsim import SimulationApp

        app = SimulationApp(
            {
                "headless": True,
                "hide_ui": True,
                "disable_viewport_updates": True,
                "renderer": "MinimalRendering",
            }
        )
        import omni.usd
        from isaaclab.sim import SimulationCfg, SimulationContext
        from pxr import PhysxSchema, UsdPhysics

        result["usdphysics_scene_has_timestep_creator"] = hasattr(
            UsdPhysics.Scene, "CreateTimeStepsPerSecondAttr"
        )
        result["physx_scene_api_has_timestep_creator"] = hasattr(
            PhysxSchema.PhysxSceneAPI, "CreateTimeStepsPerSecondAttr"
        )
        stage = _new_stage(app, omni.usd.get_context())
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)
        stage.SetTimeCodesPerSecond(240.0)
        stage.SetFramesPerSecond(60.0)
        sim = SimulationContext(
            SimulationCfg(
                physics_prim_path="/World/PhysicsScene",
                device="cpu",
                dt=PHYSICS_DT_S,
                render_interval=1,
                gravity=(0.0, 0.0, 0.0),
                enable_scene_query_support=True,
                use_fabric=False,
                create_stage_in_memory=False,
                logging_level="WARNING",
            )
        )
        sim.reset()
        physics_prim = stage.GetPrimAtPath("/World/PhysicsScene")
        physics_scene = UsdPhysics.Scene.Get(stage, "/World/PhysicsScene")
        physx_scene_api = PhysxSchema.PhysxSceneAPI.Get(stage, "/World/PhysicsScene")
        result["physics_scene_exists"] = bool(physics_prim.IsValid() and physics_scene and physx_scene_api)
        result["physics_dt_s"] = float(sim.get_physics_dt())
        result["physics_scene_time_steps_per_second"] = physx_scene_api.GetTimeStepsPerSecondAttr().Get()
        result["scene_query_enabled"] = bool(physx_scene_api.GetEnableSceneQuerySupportAttr().Get())
        gravity = physics_scene.GetGravityDirectionAttr().Get()
        magnitude = float(physics_scene.GetGravityMagnitudeAttr().Get())
        result["gravity_xyz"] = [float(gravity[i]) * magnitude for i in range(3)]
        result["decision"] = (
            "PASS"
            if result["usdphysics_scene_has_timestep_creator"] is False
            and result["physx_scene_api_has_timestep_creator"] is True
            and result["physics_scene_exists"] is True
            and result["physics_dt_s"] == PHYSICS_DT_S
            and result["scene_query_enabled"] is True
            and result["gravity_xyz"] == [0.0, 0.0, 0.0]
            else "BLOCKED_S3_R0_R5_PHYSICS_SETUP"
        )
    except BaseException:
        result["error"] = traceback.format_exc()
    # Write the probe result before teardown.  Kit teardown is performed on
    # the main thread, but a parent watchdog may need to terminate a child if
    # this Isaac version does not return from app.close().
    _write(result)
    try:
        if app is not None:
            try:
                import omni.usd

                omni.usd.get_context().close_stage()
                app.close(wait_for_replicator=False)
            except Exception:
                result["cleanup_error"] = traceback.format_exc()
    except BaseException:
        result["cleanup_error"] = traceback.format_exc()
    result["app_closed"] = "cleanup_error" not in result
    _write(result)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0 if result["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
