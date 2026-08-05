"""Probe the frozen S3 robot USD for visual prims and mass properties."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from isaacsim import SimulationApp


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--usd", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    app = SimulationApp({"headless": True, "hide_ui": True})
    try:
        import omni.usd

        app.update()
        context = omni.usd.get_context()
        context.open_stage(str(args.usd.resolve()))
        for _ in range(300):
            app.update()
            if not context.is_loading():
                break
        stage = context.get_stage()
        stage.Load()
        mesh_paths = []
        prim_type_counts = Counter()
        applied_schema_counts = Counter()
        all_prim_paths = []
        rigid_records = []
        mass_records = []
        for prim in stage.Traverse():
            path = str(prim.GetPath())
            all_prim_paths.append(path)
            prim_type_counts[prim.GetTypeName() or "<untyped>"] += 1
            for schema in prim.GetAppliedSchemas():
                applied_schema_counts[schema] += 1
            if prim.GetTypeName() == "Mesh":
                mesh_paths.append(path)
            mass = prim.GetAttribute("physics:mass")
            center = prim.GetAttribute("physics:centerOfMass")
            diagonal = prim.GetAttribute("physics:diagonalInertia")
            principal = prim.GetAttribute("physics:principalAxes")
            if prim.HasAPI("PhysicsRigidBodyAPI") or prim.HasAPI("PhysxRigidBodyAPI") or any(attr.IsValid() for attr in (mass, center, diagonal, principal)):
                record = {
                    "prim_path": path,
                    "type_name": prim.GetTypeName(),
                    "mass_kg": float(mass.Get()) if mass.IsValid() and mass.Get() is not None else None,
                    "center_of_mass_m": list(center.Get()) if center.IsValid() and center.Get() is not None else None,
                    "diagonal_inertia_kg_m2": list(diagonal.Get()) if diagonal.IsValid() and diagonal.Get() is not None else None,
                    "principal_axes": str(principal.Get()) if principal.IsValid() and principal.Get() is not None else None,
                    "has_rigid_body_api": bool(prim.HasAPI("PhysicsRigidBodyAPI") or prim.HasAPI("PhysxRigidBodyAPI")),
                }
                rigid_records.append(record)
                if record["mass_kg"] is not None or record["center_of_mass_m"] is not None or record["diagonal_inertia_kg_m2"] is not None:
                    mass_records.append(record)
        payload = {
            "source_usd": str(args.usd.resolve()),
            "source_sha256": sha256(args.usd),
            "stage_root_prims": [str(prim.GetPath()) for prim in stage.GetPseudoRoot().GetChildren()],
            "root_layer_sublayers": list(stage.GetRootLayer().subLayerPaths),
            "root_layer_external_references": list(stage.GetRootLayer().GetExternalReferences()),
            "mesh_prim_count": len(mesh_paths),
            "mesh_prims": mesh_paths,
            "prim_type_counts": dict(sorted(prim_type_counts.items())),
            "applied_schema_counts": dict(sorted(applied_schema_counts.items())),
            "prim_paths": all_prim_paths,
            "visual_prim_properties": {
                path: {
                    "properties": [str(name) for name in stage.GetPrimAtPath(path).GetPropertyNames()],
                    "attributes": {
                        str(name): str(stage.GetPrimAtPath(path).GetAttribute(name).Get())
                        for name in stage.GetPrimAtPath(path).GetPropertyNames()
                        if stage.GetPrimAtPath(path).GetAttribute(name).IsValid()
                    },
                    "relationships": {
                        str(name): [str(target) for target in stage.GetPrimAtPath(path).GetRelationship(name).GetTargets()]
                        for name in stage.GetPrimAtPath(path).GetPropertyNames()
                        if stage.GetPrimAtPath(path).GetRelationship(name).IsValid()
                    },
                }
                for path in all_prim_paths
                if "/visuals" in path
            },
            "rigid_body_or_mass_records": rigid_records,
            "mass_records": mass_records,
            "mass_property_count": len(mass_records),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str), flush=True)
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
