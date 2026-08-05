"""Import the materialized official Delta URDF through Isaac Sim's importer."""

from __future__ import annotations

import argparse

from isaacsim import SimulationApp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--urdf", required=True)
    parser.add_argument("--usd", required=True)
    args = parser.parse_args()
    app = SimulationApp({"headless": True, "hide_ui": True})
    try:
        import omni.kit.commands
        import omni.usd

        app.update()
        status, config = omni.kit.commands.execute("URDFCreateImportConfig")
        print("URDF_CONFIG", status, flush=True)
        config.merge_fixed_joints = False
        config.fix_base = False
        config.make_default_prim = True
        config.create_physics_scene = True
        config.import_inertia_tensor = True
        status, result = omni.kit.commands.execute(
            "URDFParseAndImportFile",
            urdf_path=args.urdf,
            import_config=config,
            dest_path=args.usd,
            get_articulation_root=True,
        )
        for _ in range(30):
            app.update()
        stage = omni.usd.get_context().get_stage()
        prims = [str(prim.GetPath()) for prim in stage.Traverse()]
        joints = [path for path in prims if "Joint" in path or "m1_1" in path or "m2_1" in path or "m3_1" in path]
        print(
            "DELTA_IMPORT_RESULT",
            {"status": bool(status), "result": str(result), "prim_count": len(prims), "joint_like_prims": joints[:20]},
            flush=True,
        )
        return 0 if status else 1
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
