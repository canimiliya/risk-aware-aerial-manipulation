"""Probe imported URDF joint schemas and runtime state without changing repository assets."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from isaacsim import SimulationApp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--robot-usd", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    app = SimulationApp({"headless": True, "hide_ui": True})
    try:
        import omni.usd
        from pxr import UsdGeom

        future = asyncio.ensure_future(omni.usd.get_context().new_stage_async())
        while not future.done():
            app.update()
        stage = omni.usd.get_context().get_stage()
        robot = stage.DefinePrim("/World/Robot", "Xform")
        robot.GetReferences().AddReference(str(Path(args.robot_usd).resolve()))
        for _ in range(40):
            app.update()
        result = {"robot_root": "/World/Robot", "joints": []}
        for prim in stage.Traverse():
            path = str(prim.GetPath())
            if not path.startswith("/World/Robot/body/joints/"):
                continue
            attrs = {}
            for attr in prim.GetAttributes():
                name = attr.GetName()
                if name.startswith(("physics:", "drive:", "state:")):
                    try:
                        value = attr.Get()
                        attrs[name] = str(value)
                    except Exception as exc:  # pragma: no cover - simulator probe
                        attrs[name] = f"<read-error:{exc!r}>"
            result["joints"].append(
                {
                    "path": path,
                    "type": prim.GetTypeName(),
                    "applied_schemas": list(prim.GetAppliedSchemas()),
                    "attributes": attrs,
                }
            )
        result["joints"].sort(key=lambda item: item["path"])
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("JOINT_PRIM_PROBE_RESULT", {"joint_count": len(result["joints"]), "output": str(output)}, flush=True)
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
