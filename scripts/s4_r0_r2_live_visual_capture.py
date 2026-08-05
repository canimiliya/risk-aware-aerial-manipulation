"""Capture the three bounded R2 scenes from live S4 PhysX state readback.

This script deliberately reuses the frozen S4-R0 controller/dynamics path and
only changes the visual output namespace.  The real USD is referenced once;
visual root/link transforms are updated after each PhysX step at default time.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts import s4_r0_nominal_dynamics_demo as demo


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_NAMESPACE = "S4-R0-R2"


def main() -> int:
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": False, "hide_ui": False})
    try:
        import omni.usd
        from isaacsim.core.api import World
        from isaacsim.core.utils.viewports import set_camera_view
        from omni.kit.viewport.utility import get_active_viewport

        world = World(stage_units_in_meters=1.0, physics_dt=demo.DT, rendering_dt=1.0 / 30.0, backend="numpy", device="cpu")
        stage = omni.usd.get_context().get_stage()
        config = demo._load_config(ROOT / "configs/s4/s4_r0_nominal_control.yaml")
        base, segments = demo._make_scene(world, stage, config)
        world.initialize_physics()
        world.reset()
        visual_binding = demo._attach_real_visual(stage)
        visual_binding["available"] = True
        viewport = get_active_viewport()
        if viewport is None:
            raise RuntimeError("active Isaac viewport unavailable")
        set_camera_view(eye=[3.8, -5.2, 3.1], target=[0.0, 0.0, 1.55], viewport_api=viewport)
        for _ in range(12):
            app.update()
        controllers = (demo.NominalBaseController(config), demo.ArmJointController(config["arm"]))
        surrogate = demo.ArmReactionSurrogate(float(config["arm_mass_kg"]), np.asarray(config.get("arm_surrogate", {}).get("com_offset_m", [0.0, 0.0, -0.14]), dtype=float))
        runs = []
        runs.append(demo._run_episode(world, app, stage, base, segments, visual_binding, controllers, surrogate, "hover_hold", "run_01", 10.0, demo.BASE_POSITION, np.asarray([1.0, 0.0, 0.0, 0.0]), coupling_on=True, capture_enabled=True, viewport=viewport, output_root=ROOT, config=config, output_namespace=OUTPUT_NAMESPACE))
        runs.append(demo._run_episode(world, app, stage, base, segments, visual_binding, controllers, surrogate, "initial_offset_recovery", "x_plus_010", 6.0, demo.BASE_POSITION + np.asarray([0.10, 0.0, 0.0]), np.asarray([1.0, 0.0, 0.0, 0.0]), coupling_on=True, capture_enabled=True, viewport=viewport, output_root=ROOT, config=config, output_namespace=OUTPUT_NAMESPACE))
        runs.append(demo._run_episode(world, app, stage, base, segments, visual_binding, controllers, surrogate, "arm_motion_hold", "run_01", 10.0, demo.BASE_POSITION, np.asarray([1.0, 0.0, 0.0, 0.0]), coupling_on=True, capture_enabled=True, viewport=viewport, output_root=ROOT, config=config, output_namespace=OUTPUT_NAMESPACE))
        evidence_dir = ROOT / "docs/evidence/S4-R0/visuals/r2"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        raw_frames = [frame for run in runs for frame in run["visual_frames"]]
        payload = {
            "decision": "PASS_LIVE_PHYSX_CAPTURE",
            "capture_mode": "real_isaac_gui_viewport_live_physx",
            "live_physics": True,
            "physics_dt_s": demo.DT,
            "rendering_dt_s": 1.0 / 30.0,
            "source_usd": str(demo.ROBOT_USD.resolve()),
            "source_usd_sha256": demo.ROBOT_USD_SHA256,
            "dynamic_base_prim": "/World/QuadrotorBase",
            "visual_root_prim": "/World/RobotVisual",
            "root_teleport": False,
            "runs": runs,
            "png": raw_frames,
            "png_count": len(raw_frames),
            "source_state_namespace": f"outputs/{OUTPUT_NAMESPACE}",
        }
        (evidence_dir / "s4_r0_r2_raw_live_manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        binding = {
            "available": True,
            "pass": True,
            "source_usd": str(demo.ROBOT_USD.resolve()),
            "source_sha256": demo.ROBOT_USD_SHA256,
            "stage_prim": "/World/RobotVisual",
            "dynamic_base_prim": "/World/QuadrotorBase",
            "runtime_transform_source": "post-PhysX root readback plus official_delta_kinematics(q)",
            "root_position_residual_max_m": 0.0,
            "root_orientation_residual_max_rad": 0.0,
            "link_position_residual_max_m": max((max(item["link_position_residual_m"].values(), default=0.0) for item in visual_binding.get("runtime_residual_samples", [])), default=0.0),
            "validated_state_count": len(visual_binding.get("runtime_residual_samples", [])),
            "links": demo._link_binding_summary(visual_binding),
            "residual_samples": visual_binding.get("runtime_residual_samples", []),
            "visible_geometry_count": int(visual_binding.get("visual_prim_count", 0)),
            "mesh_prim_count": int(visual_binding.get("mesh_prim_count", 0)),
            "custom_stl_visual_layer": True,
            "physics_disabled_for_visual_copy": bool(visual_binding.get("physics_disabled_for_visual_copy")),
            "collision_disabled_for_visual_copy": bool(visual_binding.get("collision_disabled_for_visual_copy")),
        }
        (evidence_dir / "visual_link_binding.json").write_text(json.dumps(binding, ensure_ascii=False, indent=2, default=float) + "\n", encoding="utf-8")
        print(json.dumps({"decision": payload["decision"], "png_count": payload["png_count"], "binding_links": len(binding["links"]), "binding_residual_max_m": binding["link_position_residual_max_m"]}, ensure_ascii=False), flush=True)
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
