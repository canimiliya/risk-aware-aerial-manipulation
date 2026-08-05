"""Inspect composed transforms and visual child metadata for the frozen S3 USD."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--usd", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "hide_ui": True})
    try:
        import omni.usd
        from pxr import UsdGeom

        context = omni.usd.get_context()
        context.new_stage()
        stage = context.get_stage()
        root = stage.DefinePrim("/World/RobotVisual", "Xform")
        asset = stage.DefinePrim("/World/RobotVisual/Asset", "Xform")
        asset.GetReferences().AddReference(str(Path(args.usd).resolve()))
        for _ in range(60):
            app.update()
        rows = []
        wanted = ("body", "end_effector", "AA_1", "AA_2", "AA_3", "TA_1l", "TA_1r", "TA_2l", "TA_2r", "TA_3l", "TA_3r")
        for prim in stage.Traverse():
            path = str(prim.GetPath())
            if not any(path.endswith("/body/" + name) for name in wanted):
                continue
            item = {"path": path, "type": prim.GetTypeName(), "schemas": list(prim.GetAppliedSchemas()), "children": []}
            if prim.IsA(UsdGeom.Xformable):
                xf = UsdGeom.Xformable(prim)
                ops = xf.GetOrderedXformOps()
                item["xform_ops"] = [{"name": str(op.GetOpName()), "value": str(op.Get())} for op in ops]
                try:
                    item["local_matrix"] = [[float(v) for v in row] for row in xf.GetLocalTransformation()[0]]
                except Exception as exc:
                    item["local_matrix_error"] = repr(exc)
            for child in prim.GetAllChildren():
                item["children"].append({"path": str(child.GetPath()), "type": child.GetTypeName(), "schemas": list(child.GetAppliedSchemas()), "properties": [p.GetName() for p in child.GetProperties()]})
            rows.append(item)
        payload = {"usd": str(Path(args.usd).resolve()), "rows": rows}
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        print(json.dumps({"rows": len(rows), "output": str(output.resolve())}), flush=True)
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
