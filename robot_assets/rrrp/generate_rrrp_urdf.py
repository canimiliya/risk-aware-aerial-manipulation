"""Generate the RRRP URDF from the single authoritative design YAML."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent


def load_design(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def total_mass(design: dict, name: str) -> float:
    item = design["mass_properties"]["links"][name]
    return float(item["structural_mass"]) + float(item["motor_lumped_mass"])


def inertia_box(mass: float, dims: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = dims
    return (mass * (y * y + z * z) / 12.0, mass * (x * x + z * z) / 12.0, mass * (x * x + y * y) / 12.0)


def link_inertial(design: dict, name: str) -> tuple[float, tuple[float, float, float], tuple[float, float, float]]:
    geometry = design["geometry"]
    length = {"link1": geometry["L1"], "link2": geometry["L2"], "link3": geometry["L3"], "slider": geometry["p_stroke"]}.get(name)
    if length is None:
        dims = (geometry["gripper_mount_length"], geometry["gripper_mount_width"], geometry["gripper_mount_height"])
        com = (dims[0] / 2.0, 0.0, 0.0)
    else:
        dims = (length, geometry["link_cross_section"], geometry["link_cross_section"])
        com = (length / 2.0, 0.0, 0.0)
    mass = total_mass(design, name)
    return mass, com, inertia_box(mass, dims)


def xml_vec(values: tuple[float, ...]) -> str:
    return " ".join(f"{float(value):.12g}" for value in values)


def generate(design: dict) -> str:
    g = design["geometry"]
    j = design["joints"]
    chunks = [
        '<?xml version="1.0"?>',
        '<robot name="rrrp_arm">',
        '  <link name="fixed_arm_base"/>',
    ]
    for name in ("link1", "link2", "link3", "slider", "gripper_mount"):
        mass, com, inertia = link_inertial(design, name)
        if name == "slider":
            dims = (g["p_stroke"], g["link_cross_section"] * 0.8, g["link_cross_section"] * 0.8)
        elif name == "gripper_mount":
            dims = (g["gripper_mount_length"], g["gripper_mount_width"], g["gripper_mount_height"])
        else:
            dims = (g[{"link1": "L1", "link2": "L2", "link3": "L3"}[name]], g["link_cross_section"], g["link_cross_section"])
        chunks += [
            f'  <link name="{name}">',
            f'    <inertial><origin xyz="{xml_vec(com)}"/><mass value="{mass:.12g}"/><inertia ixx="{inertia[0]:.12g}" ixy="0" ixz="0" iyy="{inertia[1]:.12g}" iyz="0" izz="{inertia[2]:.12g}"/></inertial>',
            f'    <visual><origin xyz="{xml_vec(com)}"/><geometry><box size="{xml_vec(dims)}"/></geometry></visual>',
            f'    <collision><origin xyz="{xml_vec(com)}"/><geometry><box size="{xml_vec(dims)}"/></geometry></collision>',
            '  </link>',
        ]
    joints = [
        ("q1", "fixed_arm_base", "link1", (0.0, 0.0, 0.0), "revolute"),
        ("q2", "link1", "link2", (g["L1"], 0.0, 0.0), "revolute"),
        ("q3", "link2", "link3", (g["L2"], 0.0, 0.0), "revolute"),
        ("d", "link3", "slider", (g["L3"], 0.0, 0.0), "prismatic"),
    ]
    for name, parent, child, xyz, kind in joints:
        spec = j[name]
        chunks += [
            f'  <joint name="{name}" type="{kind}">',
            f'    <parent link="{parent}"/><child link="{child}"/>',
            f'    <origin xyz="{xml_vec(xyz)}" rpy="0 0 0"/><axis xyz="{xml_vec(tuple(spec["axis"]))}"/>',
            f'    <limit lower="{spec["lower"]}" upper="{spec["upper"]}" effort="{spec["max_effort"]}" velocity="{spec["max_velocity"]}"/>',
            f'    <dynamics damping="{spec["damping"]}" friction="{spec["friction"]}"/>',
            '  </joint>',
        ]
    chunks += [
        f'  <joint name="gripper_mount_fixed" type="fixed"><parent link="slider"/><child link="gripper_mount"/><origin xyz="{xml_vec((g["p_stroke"], 0.0, 0.0))}" rpy="0 0 0"/></joint>',
        '</robot>',
    ]
    return "\n".join(chunks) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", type=Path, default=ROOT / "rrrp_design.yaml")
    parser.add_argument("--output", type=Path, default=ROOT / "rrrp_arm.urdf")
    args = parser.parse_args()
    args.output.write_text(generate(load_design(args.design)), encoding="utf-8")
    print(f"RRRP_URDF_WRITTEN {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
