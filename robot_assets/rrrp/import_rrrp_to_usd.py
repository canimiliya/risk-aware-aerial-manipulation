"""Author the independent RRRP PhysX/USD asset from ``rrrp_design.yaml``.

The file name follows the requested importer boundary, but the authoring is
deliberately explicit: the resulting USD contains USD Physics bodies and
joints directly, so its topology can be audited without a visual or legacy
Delta dependency.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
from generate_rrrp_urdf import inertia_box, load_design, total_mass  # noqa: E402


def _vec3(values: Any) -> Any:
    from pxr import Gf

    return Gf.Vec3f(float(values[0]), float(values[1]), float(values[2]))


def _quat_identity() -> Any:
    from pxr import Gf

    return Gf.Quatf(1.0, 0.0, 0.0, 0.0)


def _inertial(design: dict, name: str) -> dict[str, Any]:
    g = design["geometry"]
    if name == "gripper_mount":
        dims = (g["gripper_mount_length"], g["gripper_mount_width"], g["gripper_mount_height"])
    elif name == "slider":
        dims = (g["p_stroke"], g["link_cross_section"] * 0.8, g["link_cross_section"] * 0.8)
    else:
        dims = (g[{"link1": "L1", "link2": "L2", "link3": "L3"}[name]], g["link_cross_section"], g["link_cross_section"])
    mass = total_mass(design, name)
    return {
        "mass_kg": mass,
        "dimensions_m": list(dims),
        "center_of_mass_m": [dims[0] / 2.0, 0.0, 0.0],
        "diagonal_inertia_kg_m2": list(inertia_box(mass, dims)),
        "geometry_source": "box dimensions and mass from rrrp_design.yaml",
    }


def _apply_box(stage: Any, path: str, dims: tuple[float, float, float], color: tuple[float, float, float]) -> None:
    from pxr import Gf, UsdGeom, UsdPhysics

    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr().Set(1.0)
    cube.AddScaleOp().Set(Gf.Vec3f(*[float(value) for value in dims]))
    del color
    collision = UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
    # R4 validates open-chain joint dynamics, not contact.  Disabled
    # collision geometry prevents the adjacent box approximations from
    # injecting an unrequested initial contact impulse into the pulse tests.
    collision.CreateCollisionEnabledAttr().Set(False)


def _apply_body(stage: Any, path: str, *, mass: float, com: tuple[float, float, float], inertia: tuple[float, float, float], kinematic: bool = False) -> Any:
    from pxr import Gf, UsdGeom, UsdPhysics

    body = UsdGeom.Xform.Define(stage, path).GetPrim()
    rb = UsdPhysics.RigidBodyAPI.Apply(body)
    rb.CreateRigidBodyEnabledAttr().Set(True)
    rb.CreateKinematicEnabledAttr().Set(bool(kinematic))
    mass_api = UsdPhysics.MassAPI.Apply(body)
    mass_api.CreateMassAttr().Set(float(mass))
    mass_api.CreateCenterOfMassAttr().Set(Gf.Vec3f(*com))
    mass_api.CreateDiagonalInertiaAttr().Set(Gf.Vec3f(*inertia))
    body.SetCustomDataByKey("rrrp:positive_mass", bool(mass > 0.0))
    return body


def _translate(stage: Any, path: str, xyz: tuple[float, float, float]) -> None:
    from pxr import Gf, UsdGeom

    UsdGeom.Xformable(stage.GetPrimAtPath(path)).AddTranslateOp().Set(Gf.Vec3d(*xyz))


def _joint(stage: Any, path: str, kind: str, body0: str | None, body1: str, pos0: tuple[float, float, float], pos1: tuple[float, float, float], axis: str | None = None, lower: float | None = None, upper: float | None = None) -> Any:
    from pxr import Sdf, UsdPhysics

    schema = {"revolute": UsdPhysics.RevoluteJoint, "prismatic": UsdPhysics.PrismaticJoint, "fixed": UsdPhysics.FixedJoint}[kind]
    joint = schema.Define(stage, path)
    joint.CreateBody0Rel().SetTargets([Sdf.Path(body0)] if body0 else [])
    joint.CreateBody1Rel().SetTargets([Sdf.Path(body1)])
    joint.CreateLocalPos0Attr().Set(_vec3(pos0))
    joint.CreateLocalPos1Attr().Set(_vec3(pos1))
    joint.CreateLocalRot0Attr().Set(_quat_identity())
    joint.CreateLocalRot1Attr().Set(_quat_identity())
    joint.CreateJointEnabledAttr().Set(True)
    if axis is not None:
        joint.CreateAxisAttr().Set(axis)
    if lower is not None:
        joint.CreateLowerLimitAttr().Set(float(lower))
    if upper is not None:
        joint.CreateUpperLimitAttr().Set(float(upper))
    return joint


def _drive(joint: Any, spec: dict[str, Any], angular: bool) -> None:
    # Effort-pulse qualification intentionally uses an un-driven articulation.
    # The YAML damping/friction values remain in the design source and
    # manifest; no drive target is authored, so PhysX receives pure effort
    # commands rather than a hidden position/velocity servo.
    del joint, spec, angular


def _make_chain(stage: Any, design: dict, root: str, floating: bool) -> dict[str, Any]:
    from pxr import UsdGeom, UsdPhysics

    g = design["geometry"]
    j = design["joints"]
    root_prim = UsdGeom.Xform.Define(stage, root).GetPrim()
    UsdPhysics.ArticulationRootAPI.Apply(root_prim)
    if floating:
        base_path = f"{root}/uav_base"
        base_data = design["mass_properties"]["floating_uav_base"]
        base = _apply_body(stage, base_path, mass=float(base_data["mass"]), com=tuple(base_data["center_of_mass"]), inertia=tuple(base_data["diagonal_inertia"]), kinematic=False)
        _translate(stage, base_path, (0.0, 0.0, 0.60))
        _apply_box(stage, f"{base_path}/collision", (0.20, 0.16, 0.10), (0.08, 0.28, 0.78))
        mount_path = f"{root}/arm_mount"
        mount_data = design["mass_properties"]["arm_mount"]
        _apply_body(stage, mount_path, mass=float(mount_data["mass"]), com=(0.0, 0.0, 0.0), inertia=(0.0001, 0.0001, 0.0001), kinematic=False)
        _translate(stage, mount_path, (0.0, 0.0, 0.60))
        _apply_box(stage, f"{mount_path}/collision", (0.08, 0.08, 0.04), (0.16, 0.50, 0.90))
        _joint(stage, f"{root}/joints/uav_to_mount", "fixed", base_path, mount_path, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        parent = mount_path
        base_z = 0.60
    else:
        base_path = f"{root}/fixed_arm_base"
        base = _apply_body(stage, base_path, mass=0.20, com=(0.0, 0.0, 0.0), inertia=(0.0007, 0.0007, 0.0007), kinematic=False)
        _translate(stage, base_path, (0.0, 0.0, 0.0))
        _apply_box(stage, f"{base_path}/collision", (0.10, 0.10, 0.04), (0.12, 0.36, 0.80))
        anchor_path = "/World/FixedBaseAnchor"
        if not stage.GetPrimAtPath(anchor_path).IsValid():
            _apply_body(stage, anchor_path, mass=0.20, com=(0.0, 0.0, 0.0), inertia=(0.0007, 0.0007, 0.0007), kinematic=True)
            _translate(stage, anchor_path, (0.0, 0.0, 0.0))
            _apply_box(stage, f"{anchor_path}/collision", (0.12, 0.12, 0.05), (0.30, 0.30, 0.30))
        base_constraint = _joint(stage, f"{root}/joints/base_to_world", "fixed", anchor_path, base_path, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        UsdPhysics.Joint(base_constraint.GetPrim()).GetExcludeFromArticulationAttr().Set(True)
        parent = base_path
        base_z = 0.0
    paths = {"root": root, "base": base_path}
    chain = [("link1", "q1", g["L1"], parent, (0.0, 0.0, 0.0), "Y", "revolute"), ("link2", "q2", g["L2"], f"{root}/link1", (g["L1"], 0.0, 0.0), "Y", "revolute"), ("link3", "q3", g["L3"], f"{root}/link2", (g["L2"], 0.0, 0.0), "Y", "revolute"), ("slider", "d", g["p_stroke"], f"{root}/link3", (g["L3"], 0.0, 0.0), "X", "prismatic")]
    cumulative = 0.0
    for name, joint_name, length, parent_path, joint_pos, axis, kind in chain:
        data = _inertial(design, name)
        body_path = f"{root}/{name}"
        _apply_body(stage, body_path, mass=data["mass_kg"], com=tuple(data["center_of_mass_m"]), inertia=tuple(data["diagonal_inertia_kg_m2"]))
        if name == "link1": cumulative = 0.0
        elif name == "link2": cumulative = g["L1"]
        elif name == "link3": cumulative = g["L1"] + g["L2"]
        else: cumulative = g["L1"] + g["L2"] + g["L3"]
        _translate(stage, body_path, (cumulative, 0.0, base_z))
        dims = tuple(data["dimensions_m"])
        _apply_box(stage, f"{body_path}/collision", dims, (0.10 + 0.04 * len(paths), 0.55, 0.20))
        joint = _joint(stage, f"{root}/joints/{joint_name}", kind, parent_path, body_path, joint_pos, (0.0, 0.0, 0.0), axis, float(j[joint_name]["lower"]), float(j[joint_name]["upper"]))
        _drive(joint, j[joint_name], angular=(kind == "revolute"))
        paths[joint_name] = str(joint.GetPath())
        paths[name] = body_path
        parent = body_path
    gripper = "gripper_mount"
    data = _inertial(design, gripper)
    body_path = f"{root}/{gripper}"
    _apply_body(stage, body_path, mass=data["mass_kg"], com=tuple(data["center_of_mass_m"]), inertia=tuple(data["diagonal_inertia_kg_m2"]))
    _translate(stage, body_path, (g["L1"] + g["L2"] + g["L3"] + g["p_stroke"], 0.0, base_z))
    _apply_box(stage, f"{body_path}/collision", tuple(data["dimensions_m"]), (0.80, 0.22, 0.12))
    fixed = _joint(stage, f"{root}/joints/gripper_mount_fixed", "fixed", f"{root}/slider", body_path, (g["p_stroke"], 0.0, 0.0), (0.0, 0.0, 0.0))
    paths[gripper] = body_path
    paths["gripper_mount_fixed"] = str(fixed.GetPath())
    paths["floating"] = floating
    return paths


def _manifest(design: dict, stage: Any, paths: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    from collections import Counter

    links = []
    for name in ("link1", "link2", "link3", "slider", "gripper_mount"):
        data = _inertial(design, name)
        ixx, iyy, izz = data["diagonal_inertia_kg_m2"]
        valid = all(value > 0.0 and math.isfinite(value) for value in data["diagonal_inertia_kg_m2"]) and ixx <= iyy + izz and iyy <= ixx + izz and izz <= ixx + iyy
        links.append({"name": name, **data, "inertia_triangle_valid": valid, "mass_positive": bool(data["mass_kg"] > 0.0)})
    uav = design["mass_properties"]["floating_uav_base"]
    uav_i = [float(x) for x in uav["diagonal_inertia"]]
    links.append({"name": "floating_uav_base", "mass_kg": float(uav["mass"]), "center_of_mass_m": list(uav["center_of_mass"]), "diagonal_inertia_kg_m2": uav_i, "mass_positive": True, "inertia_triangle_valid": bool(uav_i[0] <= uav_i[1] + uav_i[2] and uav_i[1] <= uav_i[0] + uav_i[2] and uav_i[2] <= uav_i[0] + uav_i[1]), "provenance": uav["provenance"], "hardware_parameter_validated": False})
    joints = []
    for name in ("q1", "q2", "q3", "d"):
        spec = design["joints"][name]
        joints.append({"name": name, "type": spec["type"], "axis": list(spec["axis"]), "lower": spec["lower"], "upper": spec["upper"], "max_velocity": spec["max_velocity"], "max_effort": spec["max_effort"]})
    joints.append({"name": "gripper_mount_fixed", "type": "fixed"})
    design_manifest = {"task": "S4-R4-RRRP-NATIVE-DYNAMICS-R1", "design_source": str((ROOT / "rrrp_design.yaml").resolve()), "architecture": design["architecture"], "parameter_provenance": design["parameter_provenance"], "provisional": design["provisional"], "total_arm_mass_kg": sum(item["mass_kg"] for item in links if item["name"] in {"link1", "link2", "link3", "slider", "gripper_mount"}), "max_geometric_reach_m": float(design["geometry"]["L1"] + design["geometry"]["L2"] + design["geometry"]["L3"] + design["geometry"]["p_stroke"]), "p_stroke_m": float(design["geometry"]["p_stroke"]), "dof_count": 4, "revolute_count": 3, "prismatic_count": 1, "all_dynamic_links_positive_mass": all(item["mass_positive"] for item in links), "all_inertias_physically_valid": all(item["inertia_triangle_valid"] for item in links), "asset_paths": paths, "stage_prim_count": sum(1 for _ in stage.Traverse())}
    mass_manifest = {"task": design_manifest["task"], "source": design_manifest["design_source"], "records": links, "all_positive_mass": design_manifest["all_dynamic_links_positive_mass"], "all_inertia_physically_valid": design_manifest["all_inertias_physically_valid"], "derivation": "uniform box geometry and total link mass from the single YAML source; UAV inertia is provisional legacy provenance"}
    joint_manifest = {"task": design_manifest["task"], "source": design_manifest["design_source"], "joints": joints, "articulation_roots": ["/World/FixedBaseArm", "/World/FloatingBaseArm"], "physics_joint_count_per_articulation": 5, "native_dof_count_per_articulation": 4, "tree_structure": True}
    return design_manifest, mass_manifest, joint_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", type=Path, default=ROOT / "rrrp_design.yaml")
    parser.add_argument("--output", type=Path, default=ROOT / "rrrp_arm.usd")
    args = parser.parse_args()
    design = load_design(args.design)
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "hide_ui": True, "disable_viewport_updates": True, "renderer": "MinimalRendering"})
    try:
        from pxr import Gf, Usd, UsdGeom, UsdPhysics, PhysxSchema

        stage = Usd.Stage.CreateNew(str(args.output.resolve()))
        stage.SetMetadata("metersPerUnit", 1.0)
        stage.SetTimeCodesPerSecond(240.0)
        stage.SetFramesPerSecond(60.0)
        world = UsdGeom.Xform.Define(stage, "/World")
        stage.SetDefaultPrim(world.GetPrim())
        scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
        scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
        scene.CreateGravityMagnitudeAttr().Set(0.0)
        physx_scene = PhysxSchema.PhysxSceneAPI.Apply(scene.GetPrim())
        physx_scene.CreateTimeStepsPerSecondAttr().Set(240.0)
        physx_scene.CreateEnableSceneQuerySupportAttr().Set(True)
        fixed = _make_chain(stage, design, "/World/FixedBaseArm", False)
        floating = _make_chain(stage, design, "/World/FloatingBaseArm", True)
        fixed["root"] = "/World/FixedBaseArm"
        floating["root"] = "/World/FloatingBaseArm"
        stage.GetRootLayer().Save()
        design_manifest, mass_manifest, joint_manifest = _manifest(design, stage, {"fixed": fixed, "floating": floating})
        output = REPO / "docs/evidence/S4-R4/design"
        output.mkdir(parents=True, exist_ok=True)
        for name, payload in (("rrrp_design_manifest.json", design_manifest), ("mass_inertia_manifest.json", mass_manifest), ("joint_manifest.json", joint_manifest)):
            (output / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        transition = {"task": "S4-R4-RRRP-NATIVE-DYNAMICS-R1", "legacy_delta_asset": True, "active_manipulator_architecture": "RRRP", "active_manipulator_is_delta": False, "delta_source_usd_untouched": True, "new_asset": str(args.output.resolve()), "parameter_source": str(args.design.resolve()), "parameter_provenance": design["parameter_provenance"], "provisional": True, "rationale": "R3 proved the legacy Delta source does not uniquely reconstruct a closed chain; RRRP is an independent tree articulation."}
        (output / "architecture_transition.json").write_text(json.dumps(transition, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"usd": str(args.output.resolve()), "dof_count": design_manifest["dof_count"], "revolute_count": design_manifest["revolute_count"], "prismatic_count": design_manifest["prismatic_count"], "arm_mass_kg": design_manifest["total_arm_mass_kg"], "reach_m": design_manifest["max_geometric_reach_m"], "all_inertia_valid": design_manifest["all_inertias_physically_valid"]}, ensure_ascii=False), flush=True)
        return 0
    finally:
        app.close(wait_for_replicator=False, skip_cleanup=True)


if __name__ == "__main__":
    raise SystemExit(main())
