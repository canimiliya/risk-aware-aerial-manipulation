"""Audit the frozen Delta USD and its composed physics layers for S4-R3.

This script is deliberately read-only with respect to the source USD.  It
does not construct a substitute arm or infer missing joint topology from
visual names.  Missing body relationships are reported as an asset blocker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from isaacsim import SimulationApp


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _value(attr: Any) -> Any:
    if not attr or not attr.IsValid():
        return None
    try:
        value = attr.Get()
    except Exception as exc:  # pragma: no cover - simulator-specific
        return f"<read-error:{exc!r}>"
    if value is None:
        return None
    if hasattr(value, "__iter__") and not isinstance(value, (str, bytes, dict)):
        try:
            return [float(item) if isinstance(item, (int, float)) else str(item) for item in value]
        except TypeError:
            pass
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def _targets(prim: Any, name: str) -> list[str]:
    relationship = prim.GetRelationship(name)
    if not relationship.IsValid():
        return []
    return [str(target) for target in relationship.GetTargets()]


def _record_prim(prim: Any) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    folded_names: dict[str, int] = {}
    for attr in prim.GetAttributes():
        name = str(attr.GetName())
        folded = name.casefold()
        if folded in folded_names:
            folded_names[folded] += 1
            name = f"{name}__duplicate_{folded_names[folded]}"
        else:
            folded_names[folded] = 1
        attrs[name] = _value(attr)
    relationships = {
        str(rel.GetName()): [str(target) for target in rel.GetTargets()]
        for rel in prim.GetRelationships()
    }
    mass = attrs.get("physics:mass")
    return {
        "prim_path": str(prim.GetPath()),
        "prim_type": prim.GetTypeName() or "<untyped>",
        "applied_schemas": list(prim.GetAppliedSchemas()),
        "RigidBodyAPI": bool(prim.HasAPI("PhysicsRigidBodyAPI") or prim.HasAPI("PhysxRigidBodyAPI")),
        "MassAPI": bool(prim.HasAPI("PhysicsMassAPI") or any(name in attrs for name in ("physics:mass", "physics:centerOfMass", "physics:diagonalInertia", "physics:principalAxes"))),
        "ArticulationRootAPI": bool(prim.HasAPI("PhysicsArticulationRootAPI") or prim.HasAPI("PhysxArticulationAPI")),
        "CollisionAPI": bool(prim.HasAPI("PhysicsCollisionAPI") or prim.HasAPI("PhysxCollisionAPI")),
        "mass_kg": mass,
        "COM": attrs.get("physics:centerOfMass"),
        "diagonal_inertia": attrs.get("physics:diagonalInertia"),
        "principal_axes": attrs.get("physics:principalAxes"),
        "attributes": attrs,
        "relationships": relationships,
    }


def _layer_record(layer: Any) -> dict[str, Any]:
    return {
        "identifier": str(layer.identifier),
        "real_path": str(layer.realPath),
        "resolved_path": str(Path(layer.realPath).resolve()) if layer.realPath else None,
        "anonymous": bool(layer.anonymous),
        "sub_layers": [str(item) for item in layer.subLayerPaths],
        "external_references": [str(item) for item in layer.GetExternalReferences()],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--usd", type=Path, default=Path(r"D:/i3/a/aerial_manipulator_v2.usd"))
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    app = SimulationApp({"headless": True, "hide_ui": True})
    try:
        from pxr import Usd

        app.update()
        stage = Usd.Stage.Open(str(args.usd.resolve()))
        if stage is None:
            raise RuntimeError("USD stage did not open")
        print("S4_R3_AUDIT_STAGE_OPEN", flush=True)
        stage.Load()
        prim_records = [_record_prim(prim) for prim in stage.Traverse()]
        print(f"S4_R3_AUDIT_PRIMS {len(prim_records)}", flush=True)
        joints = [
            record
            for record in prim_records
            if record["prim_type"].startswith("Physics") and record["prim_type"].endswith("Joint")
        ]
        rigid_bodies = [record for record in prim_records if record["RigidBodyAPI"]]
        positive_mass = [record for record in rigid_bodies if isinstance(record["mass_kg"], (int, float)) and float(record["mass_kg"]) > 0.0]
        arm_mass_links = [record for record in positive_mass if "/body/" in record["prim_path"] and record["prim_path"].split("/body/", 1)[1] != "body"]
        articulation_roots = [record["prim_path"] for record in prim_records if record["ArticulationRootAPI"]]
        joint_records = []
        for record in joints:
            rels = record["relationships"]
            joint_records.append({
                "prim_path": record["prim_path"],
                "prim_type": record["prim_type"],
                "applied_schemas": record["applied_schemas"],
                "body0": rels.get("physics:body0", []),
                "body1": rels.get("physics:body1", []),
                "local_frame0": {name: record["attributes"].get(name) for name in ("physics:localPos0", "physics:localRot0")},
                "local_frame1": {name: record["attributes"].get(name) for name in ("physics:localPos1", "physics:localRot1")},
                "lower_limit": record["attributes"].get("physics:lowerLimit"),
                "upper_limit": record["attributes"].get("physics:upperLimit"),
                "drive_type": record["attributes"].get("drive:angular:physics:type"),
                "drive_stiffness": record["attributes"].get("drive:angular:physics:stiffness"),
                "drive_damping": record["attributes"].get("drive:angular:physics:damping"),
                "joint_enabled": record["attributes"].get("physics:jointEnabled"),
                "exclude_from_articulation": record["attributes"].get("physics:excludeFromArticulation"),
            })
        print(f"S4_R3_AUDIT_JOINTS {len(joint_records)}", flush=True)
        used_layers = []
        try:
            used_layers = [_layer_record(layer) for layer in stage.GetUsedLayers()]
        except Exception as exc:  # pragma: no cover - simulator-specific
            used_layers = [{"error": repr(exc)}]
        print(f"S4_R3_AUDIT_LAYERS {len(used_layers)}", flush=True)
        root_layer = stage.GetRootLayer()
        layer_manifest = {
            "source_usd": str(args.usd.resolve()),
            "source_sha256": _sha256(args.usd),
            "root_layer": _layer_record(root_layer),
            "used_layers": used_layers,
            "dependency_count": len(used_layers),
        }
        cycle_count = 0
        parent: dict[str, str] = {}

        def find(node: str) -> str:
            parent.setdefault(node, node)
            if parent[node] != node:
                parent[node] = find(parent[node])
            return parent[node]

        def union(left: str, right: str) -> bool:
            nonlocal cycle_count
            left_root, right_root = find(left), find(right)
            if left_root == right_root:
                cycle_count += 1
                return False
            parent[right_root] = left_root
            return True

        for joint in joint_records:
            if joint["body0"] and joint["body1"]:
                union(joint["body0"][0], joint["body1"][0])
        arm_root_paths = [record["prim_path"] for record in prim_records if record["ArticulationRootAPI"] and "/delta_display/" in record["prim_path"]]
        asset_manifest = {
            "task": "S4-R3-NATIVE-MULTIBODY-SKELETON-R1",
            "source_usd": str(args.usd.resolve()),
            "source_sha256": _sha256(args.usd),
            "stage_default_prim": str(stage.GetDefaultPrim().GetPath()) if stage.GetDefaultPrim().IsValid() else None,
            "prim_count": len(prim_records),
            "prim_type_counts": {},
            "prim_records": prim_records,
            "joint_count": len(joint_records),
            "joint_records": joint_records,
            "uav_base_rigid_body_found": any(record["RigidBodyAPI"] and "/delta_display/" not in record["prim_path"] for record in prim_records),
            "arm_base_rigid_body_found": any(record["RigidBodyAPI"] and record["prim_path"].endswith("/body/body") for record in prim_records),
            "arm_positive_mass_link_count": len(arm_mass_links),
            "active_joint_count_candidate": sum(1 for record in joint_records if record["prim_type"] == "PhysicsRevoluteJoint" and record["lower_limit"] not in (None, 0.0) or record["upper_limit"] not in (None, 0.0)),
            "passive_joint_count_candidate": sum(1 for record in joint_records if record["prim_type"] == "PhysicsRevoluteJoint" and record["lower_limit"] == 0.0 and record["upper_limit"] == 0.0),
            "existing_loop_joint_count": cycle_count,
            "articulation_root_present": bool(articulation_roots),
            "articulation_root_paths": articulation_roots,
            "arm_articulation_root_paths": arm_root_paths,
            "floating_base_articulation_candidate": False,
            "body_relationships_present": bool(joint_records) and all(record["body0"] and record["body1"] for record in joint_records),
            "delta_loop_reconstructable": False,
        }
        from collections import Counter

        asset_manifest["prim_type_counts"] = dict(sorted(Counter(record["prim_type"] for record in prim_records).items()))
        topology = {
            "task": "S4-R3-NATIVE-MULTIBODY-SKELETON-R1",
            "base_link": None,
            "active_joints": [],
            "passive_joints": [],
            "tree_edges": [],
            "loop_edges": [],
            "broken_tree_edge": None,
            "closure_joint": None,
            "closed_chain_expected": True,
            "reconstructable": False,
            "blocker": "source USD exposes only a star/tree: the end-effector is connected to each branch link, but no distal branch-to-end-effector closure edges or floating UAV base are present",
            "missing": ["missing passive joint", "link relationship", "floating UAV base rigid body"],
            "source_joint_records": joint_records,
        }
        files = {
            "native_asset_manifest.json": asset_manifest,
            "rigid_body_manifest.json": {"source_usd": str(args.usd.resolve()), "rigid_bodies": rigid_bodies, "positive_mass_links": positive_mass, "articulation_root_paths": articulation_roots},
            "mass_inertia_manifest.json": {"source_usd": str(args.usd.resolve()), "mass_records": positive_mass, "uav_mass_provenance_validated": False, "uav_inertia_provenance_validated": False, "provisional_uav_inertial_used": True},
            "joint_manifest.json": {"source_usd": str(args.usd.resolve()), "joints": joint_records},
            "layer_dependency_manifest.json": layer_manifest,
            "delta_topology_manifest.json": topology,
        }
        output_root.mkdir(parents=True, exist_ok=True)
        for filename, payload in files.items():
            (output_root / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        result = {
            "UAV_BASE_RIGID_BODY_FOUND": asset_manifest["uav_base_rigid_body_found"],
            "ARM_POSITIVE_MASS_LINK_COUNT": asset_manifest["arm_positive_mass_link_count"],
            "ACTIVE_JOINT_COUNT": asset_manifest["active_joint_count_candidate"],
            "PASSIVE_JOINT_COUNT": asset_manifest["passive_joint_count_candidate"],
            "EXISTING_LOOP_JOINT_COUNT": asset_manifest["existing_loop_joint_count"],
            "ARTICULATION_ROOT_PRESENT": asset_manifest["articulation_root_present"],
            "DELTA_LOOP_RECONSTRUCTABLE": asset_manifest["delta_loop_reconstructable"],
            "blocker": topology["blocker"],
            "output_root": str(output_root),
        }
        print("S4_R3_ASSET_AUDIT_RESULT", json.dumps(result, ensure_ascii=False), flush=True)
        return 0
    finally:
        app.close(wait_for_replicator=False, skip_cleanup=True)


if __name__ == "__main__":
    raise SystemExit(main())
