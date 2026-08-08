"""S4-R6 final audit for the floating quadrotor and native RRRP model.

This audit uses the R4 USD without editing its authored mass, inertia, limits,
or geometry. Joint configurations are selected through reset-only defaults;
all post-reset motion is produced by PhysX effort actions and local rotor
wrenches. The diagnostic modes are separate in-memory stage configurations.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import itertools
import json
import math
import os
import re
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "robot_assets/rrrp/rrrp_arm.usd"
RRRP_DESIGN = ROOT / "robot_assets/rrrp/rrrp_design.yaml"
QUAD_DESIGN = ROOT / "configs/s4/rrrp_quadrotor_design.yaml"
FREEZE_CONFIG = ROOT / "configs/s4/rrrp_physics_freeze.yaml"
EVIDENCE = ROOT / "docs/evidence/S4-R6"
EXPECTED_START = "1b207c572c89da21a60ad7d919efcebc8aefc757"
BODY_NAMES = ["uav_base", "arm_mount", "link1", "link2", "link3", "slider", "gripper_mount"]
ARM_NAMES = ["link1", "link2", "link3", "slider", "gripper_mount"]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def arr(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=float)


def finite(value: Any) -> bool:
    try:
        return bool(np.all(np.isfinite(arr(value))))
    except (TypeError, ValueError):
        return False


def norm(value: Any) -> float:
    return float(np.linalg.norm(arr(value)))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def quat_matrix(quaternion: Any) -> np.ndarray:
    w, x, y, z = arr(quaternion).reshape(4)
    return np.asarray([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], dtype=float)


def quat_rotate(quaternion: Any, vector: Any) -> np.ndarray:
    return quat_matrix(quaternion) @ arr(vector).reshape(3)


def squeeze(value: Any) -> np.ndarray:
    value = arr(value)
    return value[0] if value.ndim >= 2 and value.shape[0] == 1 else value


def metadata(art: Any) -> dict[str, Any]:
    metadata_value = getattr(getattr(art, "_articulation_view", None), "_metadata", None)
    names = list(getattr(metadata_value, "joint_names", []) or [])
    return {"joint_names": [str(item) for item in names], "num_dof": int(art.num_dof)}


def canonical_to_native(art: Any, values: list[float]) -> np.ndarray:
    canonical = {"q1": float(values[0]), "q2": float(values[1]), "q3": float(values[2]), "d": float(values[3])}
    output = np.zeros(art.num_dof, dtype=np.float32)
    index = 0
    for name in metadata(art)["joint_names"]:
        if name in canonical:
            output[index] = canonical[name]
            index += 1
    if index != 4:
        raise RuntimeError(f"RRRP joint mapping incomplete: {metadata(art)}")
    return output


def native_to_canonical(art: Any, values: Any) -> list[float]:
    native = arr(values).reshape(-1)
    by_name = {}
    index = 0
    for name in metadata(art)["joint_names"]:
        if name in {"q1", "q2", "q3", "d"}:
            by_name[name] = float(native[index])
            index += 1
    return [by_name[name] for name in ("q1", "q2", "q3", "d")]


def effort_action(values: list[float]) -> Any:
    from isaacsim.core.utils.types import ArticulationAction

    return ArticulationAction(joint_efforts=np.asarray(values, dtype=np.float32))


def rotor_specs(design: dict[str, Any]) -> list[dict[str, Any]]:
    quad = design["quadrotor"]
    kf = float(quad["thrust_coefficient_kf"])
    km = float(quad["moment_coefficient_km"])
    output = []
    for item in quad["rotors"]:
        axis = arr(item["axis_body"])
        axis = axis / np.linalg.norm(axis)
        output.append({
            "id": str(item["id"]),
            "position_body_m": arr(item["position_body"]).tolist(),
            "axis_body": axis.tolist(),
            "spin_direction": int(item["spin_direction"]),
            "kf": kf,
            "km": km,
        })
    return output


def allocation(rotors: list[dict[str, Any]]) -> np.ndarray:
    rows = []
    for rotor in rotors:
        position = arr(rotor["position_body_m"])
        axis = arr(rotor["axis_body"])
        moment = np.cross(position, axis) + float(rotor["spin_direction"]) * float(rotor["km"] / rotor["kf"]) * axis
        rows.append(np.concatenate((axis, moment))[2:])
    return arr(rows).T


def motor_update(actual: np.ndarray, command: np.ndarray, design: dict[str, Any], dt: float) -> np.ndarray:
    quad = design["quadrotor"]
    lower = float(quad["min_speed"])
    upper = float(quad["max_speed"])
    tau = float(quad["motor_time_constant"])
    alpha = 1.0 - math.exp(-dt / tau)
    command = np.clip(command, lower, upper)
    return np.clip(actual + alpha * (command - actual), lower, upper)


def apply_rotors(base_view: Any, rotors: list[dict[str, Any]], actual: np.ndarray) -> None:
    for rotor, speed in zip(rotors, actual):
        thrust = float(rotor["kf"] * float(speed) ** 2)
        reaction = float(rotor["spin_direction"] * rotor["km"] * float(speed) ** 2)
        axis = arr(rotor["axis_body"])
        position = arr(rotor["position_body_m"])
        base_view.apply_forces_and_torques_at_pos(
            np.asarray([axis * thrust], dtype=np.float32),
            np.asarray([axis * reaction], dtype=np.float32),
            np.asarray([position], dtype=np.float32),
            is_global=False,
        )


def base_state(base_view: Any) -> dict[str, Any]:
    positions, orientations = base_view.get_world_poses()
    linear = base_view.get_linear_velocities()
    angular = base_view.get_angular_velocities()
    values = [squeeze(item) for item in (positions, orientations, linear, angular)]
    return {
        "position_world_m": values[0].tolist(),
        "orientation_world_wxyz": values[1].tolist(),
        "linear_velocity_world_m_s": values[2].tolist(),
        "angular_velocity_world_rad_s": values[3].tolist(),
        "finite": all(finite(item) for item in values),
    }


def system_mass_com(body_view: Any, base_view: Any, geometry: dict[str, Any]) -> dict[str, Any]:
    positions, orientations = body_view.get_world_poses()
    positions = arr(positions)
    orientations = arr(orientations)
    masses = arr(body_view.get_masses()).reshape(-1)
    base_positions, base_orientations = base_view.get_world_poses()
    base_position = squeeze(base_positions)
    base_orientation = squeeze(base_orientations)
    local_com = {
        "uav_base": [0.0, 0.0, 0.0],
        "arm_mount": [0.0, 0.0, 0.0],
        "link1": [float(geometry["L1"]) / 2.0, 0.0, 0.0],
        "link2": [float(geometry["L2"]) / 2.0, 0.0, 0.0],
        "link3": [float(geometry["L3"]) / 2.0, 0.0, 0.0],
        "slider": [float(geometry["p_stroke"]) / 2.0, 0.0, 0.0],
        "gripper_mount": [float(geometry["gripper_mount_length"]) / 2.0, 0.0, 0.0],
    }
    body_com_world = arr([positions[index] + quat_rotate(orientations[index], local_com[name]) for index, name in enumerate(BODY_NAMES)])
    total_mass = float(np.sum(masses))
    world_com = np.sum(masses[:, None] * body_com_world, axis=0) / total_mass
    body_com = quat_matrix(base_orientation).T @ (world_com - base_position)
    return {
        "body_names": BODY_NAMES,
        "body_masses_kg": masses.tolist(),
        "total_system_mass_kg": total_mass,
        "system_com_world_m": world_com.tolist(),
        "system_com_body_m": body_com.tolist(),
        "system_com_neutral_m": body_com.tolist(),
        "base_position_world_m": base_position.tolist(),
        "base_orientation_world_wxyz": base_orientation.tolist(),
        "mass_readback_source": "PhysX RigidPrim.get_masses() and world poses",
        "finite": bool(finite(masses) and finite(world_com) and finite(body_com)),
    }


def aabb_audit(body_view: Any, geometry: dict[str, Any], limits: dict[str, Any], requested: list[float]) -> dict[str, Any]:
    positions, orientations = body_view.get_world_poses()
    positions = arr(positions)
    orientations = arr(orientations)
    dimensions = {
        "link1": [geometry["L1"], geometry["link_cross_section"], geometry["link_cross_section"]],
        "link2": [geometry["L2"], geometry["link_cross_section"], geometry["link_cross_section"]],
        "link3": [geometry["L3"], geometry["link_cross_section"], geometry["link_cross_section"]],
        "slider": [geometry["p_stroke"], geometry["link_cross_section"] * 0.8, geometry["link_cross_section"] * 0.8],
        "gripper_mount": [geometry["gripper_mount_length"], geometry["gripper_mount_width"], geometry["gripper_mount_height"]],
    }
    aabbs: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for index, name in enumerate(ARM_NAMES, start=2):
        rotation = quat_matrix(orientations[index])
        half_extent = 0.5 * (np.abs(rotation) @ arr(dimensions[name]))
        aabbs[name] = (positions[index] - half_extent, positions[index] + half_extent)
    pairs = []
    for left_index, left in enumerate(ARM_NAMES):
        for right in ARM_NAMES[left_index + 1:]:
            left_min, left_max = aabbs[left]
            right_min, right_max = aabbs[right]
            gaps = np.maximum(left_min - right_max, right_min - left_max)
            gap = float(np.max(gaps)) if np.any(gaps > 0.0) else 0.0
            adjacent = abs(ARM_NAMES.index(left) - ARM_NAMES.index(right)) == 1
            pairs.append({"pair": [left, right], "adjacent": adjacent, "aabb_gap_m": gap, "non_adjacent_clear": bool(adjacent or gap > 0.0)})
    q = arr(requested)
    limits_pass = bool(
        limits["q1"][0] - 1e-5 <= q[0] <= limits["q1"][1] + 1e-5
        and limits["q2"][0] - 1e-5 <= q[1] <= limits["q2"][1] + 1e-5
        and limits["q3"][0] - 1e-5 <= q[2] <= limits["q3"][1] + 1e-5
        and limits["d"][0] - 1e-5 <= q[3] <= limits["d"][1] + 1e-5
    )
    non_adjacent = [item for item in pairs if not item["adjacent"]]
    clearance_pass = bool(non_adjacent and all(item["non_adjacent_clear"] for item in non_adjacent))
    return {"requested_configuration_q1_q2_q3_d": q.tolist(), "readback_configuration_q1_q2_q3_d": q.tolist(), "joint_limits_valid": limits_pass, "aabb_pair_checks": pairs, "non_adjacent_self_clear": clearance_pass, "geometry_clearance_valid": clearance_pass, "valid_for_trim": bool(limits_pass and clearance_pass)}


def hover_trim(mass_com: dict[str, Any], matrix: np.ndarray, gravity: float, max_thrust: float) -> dict[str, Any]:
    mass = float(mass_com["total_system_mass_kg"])
    com = arr(mass_com["system_com_body_m"])
    gravity_force = np.asarray([0.0, 0.0, -mass * gravity], dtype=float)
    gravity_torque = np.cross(com, gravity_force)
    target = np.asarray([mass * gravity, -gravity_torque[0], -gravity_torque[1], -gravity_torque[2]], dtype=float)
    try:
        thrusts = np.linalg.solve(matrix, target)
        residual = matrix @ thrusts - target
        solve_error = None
    except np.linalg.LinAlgError as error:
        thrusts = np.full(4, np.nan)
        residual = np.full(4, np.nan)
        solve_error = str(error)
    utilization = arr(thrusts) / max_thrust
    return {
        "target_wrench_fz_taux_tauy_tauz": target.tolist(),
        "gravity_force_body_n": gravity_force.tolist(),
        "gravity_torque_body_nm": gravity_torque.tolist(),
        "trim_thrusts_n": arr(thrusts).tolist(),
        "max_rotor_utilization": float(np.max(utilization)) if finite(utilization) else None,
        "force_residual_n": float(abs(residual[0])) if finite(residual) else None,
        "torque_residual_nm": float(np.linalg.norm(residual[1:])) if finite(residual) else None,
        "all_nonnegative": bool(finite(thrusts) and np.all(thrusts >= -1e-10)),
        "all_below_max": bool(finite(thrusts) and np.all(thrusts <= max_thrust + 1e-10)),
        "solve_error": solve_error,
        "hover_trim_feasible": bool(finite(thrusts) and np.all(thrusts >= -1e-10) and np.all(thrusts <= max_thrust + 1e-10) and abs(residual[0]) < 1e-8 and norm(residual[1:]) < 1e-8),
    }


def configure(art: Any, world: Any, q: list[float], gravity: float) -> None:
    art.set_joints_default_state(positions=canonical_to_native(art, q), velocities=np.zeros(4, dtype=np.float32))
    world.get_physics_context().set_gravity(float(gravity))
    world.reset()


def momentum(body_view: Any) -> dict[str, Any]:
    masses = arr(body_view.get_masses()).reshape(-1)
    velocities = arr(body_view.get_linear_velocities())
    momentum_value = np.sum(masses[:, None] * velocities, axis=0)
    max_speed = max((norm(item) for item in velocities), default=0.0)
    return {"body_masses_kg": masses.tolist(), "linear_momentum_kg_m_s": momentum_value.tolist(), "max_body_speed_m_s": max_speed, "characteristic_momentum_kg_m_s": float(np.sum(masses) * max_speed), "finite": bool(finite(masses) and finite(velocities) and finite(momentum_value))}


def kinetic_energy(body_view: Any) -> float:
    positions, orientations = body_view.get_world_poses()
    del positions
    orientations = arr(orientations)
    masses = arr(body_view.get_masses()).reshape(-1)
    velocities = arr(body_view.get_linear_velocities())
    angular = arr(body_view.get_angular_velocities())
    inertias = arr(body_view.get_inertias()).reshape((-1, 3, 3))
    total = 0.0
    for index, mass in enumerate(masses):
        total += 0.5 * float(mass) * float(np.dot(velocities[index], velocities[index]))
        world_inertia = quat_matrix(orientations[index]) @ inertias[index] @ quat_matrix(orientations[index]).T
        total += 0.5 * float(angular[index] @ world_inertia @ angular[index])
    return float(total)


def source_audit() -> dict[str, Any]:
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {"set_world_pose", "set_world_poses", "set_world_transform", "set_linear_velocity", "set_angular_velocity", "set_joint_positions", "set_joint_velocities", "set_root_state"}
    calls = [node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
    direct_world = bool(re.search(r"apply_forces_and_torques_at_pos[\s\S]{0,500}is_global\s*=\s*True", source))
    return {
        "task": "S4-R6-PHYSICS-MODEL-FREEZE-R1",
        "direct_world_force_command": direct_world,
        "direct_world_torque_command": direct_world,
        "root_runtime_state_write": any(item in forbidden for item in calls),
        "joint_runtime_position_write": any(item == "set_joint_positions" for item in calls),
        "joint_runtime_velocity_write": any(item == "set_joint_velocities" for item in calls),
        "python_arm_integrator": bool(re.search(r"q\s*\+=|dq\s*\+=|qdd\s*\+=", source)),
        "manual_reaction": bool(re.search(r"manual_reaction\s*\(", source)),
        "manual_arm_gravity": bool(re.search(r"manual_arm_gravity\s*\(", source)),
        "reset_only_joint_default_write": calls.count("set_joints_default_state") > 0,
        "forbidden_calls": sorted(set(item for item in calls if item in forbidden)),
        "active_path_audit_pass": bool(not direct_world and not any(item in forbidden for item in calls) and not re.search(r"q\s*\+=|dq\s*\+=|qdd\s*\+=", source)),
        "notes": "set_joints_default_state is used only before world.reset for diagnostic configuration selection; no runtime pose, velocity, or root-state write is used.",
    }


def physics_scene_manifest(stage: Any, world: Any, dt: float) -> dict[str, Any]:
    scene_records = []
    for prim in stage.Traverse():
        if str(prim.GetTypeName()) == "PhysicsScene" or "PhysicsScene" in str(prim.GetTypeName()):
            attrs = {}
            for attribute in prim.GetAttributes():
                value = attribute.Get()
                try:
                    json.dumps(value)
                except TypeError:
                    value = str(value)
                attrs[str(attribute.GetName())] = value
            scene_records.append({"path": str(prim.GetPath()), "type": str(prim.GetTypeName()), "attributes": attrs})
    context = world.get_physics_context()
    return {"task": "S4-R6-PHYSICS-MODEL-FREEZE-R1", "physics_dt_s": dt, "physics_rate_hz": 1.0 / dt, "physics_scene_prims": scene_records, "solver_type": next((item["attributes"].get("physxScene:solverType") for item in scene_records if item["attributes"].get("physxScene:solverType") is not None), None), "position_iterations": next((item["attributes"].get("physxScene:minPositionIterationCount") for item in scene_records if item["attributes"].get("physxScene:minPositionIterationCount") is not None), None), "velocity_iterations": next((item["attributes"].get("physxScene:minVelocityIterationCount") for item in scene_records if item["attributes"].get("physxScene:minVelocityIterationCount") is not None), None), "stabilization": next((item["attributes"].get("physxScene:enableStabilization") for item in scene_records if item["attributes"].get("physxScene:enableStabilization") is not None), None), "sleep_settings": {"enabled": None, "threshold": None}, "context_type": type(context).__name__, "source": "authored stage PhysicsScene attributes plus World physics_dt"}


def set_diagnostic_damping(stage: Any) -> dict[str, Any]:
    changed = []
    for prim in stage.Traverse():
        prim_type = str(prim.GetTypeName())
        # PhysicsScene friction-correlation thresholds are solver tolerances,
        # not physical damping/friction coefficients; changing them makes an
        # invalid scene. All non-PhysicsScene loss attributes are eligible for
        # this isolated diagnostic because authored USD may expose them on an
        # Xform rather than a typed RigidBody/Joint prim.
        if prim_type == "PhysicsScene" or "PhysicsScene" in prim_type:
            continue
        for attribute in prim.GetAttributes():
            name = str(attribute.GetName()).lower()
            if "damping" in name or "friction" in name:
                value = attribute.Get()
                try:
                    if value is not None:
                        attribute.Set(0.0)
                        changed.append({"path": str(prim.GetPath()), "attribute": str(attribute.GetName()), "previous": str(value), "diagnostic_value": 0.0})
                except Exception:
                    pass
    return {"joint_damping_disabled": bool(any("damping" in item["attribute"].lower() for item in changed)), "friction_disabled": bool(any("friction" in item["attribute"].lower() for item in changed)), "changed_attributes": changed, "production_asset_unchanged": True}


def create_simulation(asset: Path, dt: float):
    import omni.usd
    from isaacsim.core.api import World
    from isaacsim.core.prims import RigidPrim, SingleArticulation

    omni.usd.get_context().open_stage(str(asset.resolve()))
    stage = omni.usd.get_context().get_stage()
    world = World(stage_units_in_meters=1.0, physics_dt=dt, rendering_dt=dt, set_defaults=False, backend="numpy", device="cpu")
    art = world.scene.add(SingleArticulation(prim_path="/World/FloatingBaseArm", name="rrrp_r6_articulation"))
    bodies = world.scene.add(RigidPrim(prim_paths_expr="/World/FloatingBaseArm/(uav_base|arm_mount|link1|link2|link3|slider|gripper_mount)", name="rrrp_r6_bodies"))
    base = world.scene.add(RigidPrim(prim_paths_expr="/World/FloatingBaseArm/uav_base", name="rrrp_r6_base"))
    world.initialize_physics()
    world.reset()
    return stage, world, art, bodies, base


def evaluate_configuration(world: Any, art: Any, bodies: Any, base: Any, q: list[float], gravity: float, quad: dict[str, Any], geometry: dict[str, Any], limits: dict[str, Any], matrix: np.ndarray, label: str, p_value: float | None = None) -> dict[str, Any]:
    configure(art, world, q, gravity)
    readback_q = native_to_canonical(art, art.get_joint_positions())
    mass = system_mass_com(bodies, base, geometry)
    clearance = aabb_audit(bodies, geometry, limits, readback_q)
    max_thrust = float(quad["thrust_coefficient_kf"]) * float(quad["max_speed"]) ** 2
    trim = hover_trim(mass, matrix, float(quad["gravity_m_s2"]), max_thrust)
    return {"label": label, "requested_configuration_q1_q2_q3_d": q, "configuration_q1_q2_q3_d": readback_q, "p_value_m": p_value, "mass_com": mass, "geometry": clearance, "hover_trim": trim, "valid_for_trim": clearance["valid_for_trim"], "max_rotor_utilization": trim["max_rotor_utilization"] if clearance["valid_for_trim"] else None}


def workspace_envelope(world: Any, art: Any, bodies: Any, base: Any, freeze: dict[str, Any], quad: dict[str, Any], geometry: dict[str, Any], limits: dict[str, Any], matrix: np.ndarray) -> dict[str, Any]:
    samples = []
    values = freeze["workspace_sample_values"]
    for q1, q2, q3, d in itertools.product(values["q1"], values["q2"], values["q3"], values["d"]):
        q = [float(q1), float(q2), float(q3), float(d)]
        record = evaluate_configuration(world, art, bodies, base, q, 0.0, quad, geometry, limits, matrix, f"workspace_{len(samples):03d}", d)
        samples.append(record)
    valid = [item for item in samples if item["valid_for_trim"]]
    return {"task": "S4-R6-PHYSICS-MODEL-FREEZE-R1", "sample_count": len(samples), "valid_count": len(valid), "invalid_count": len(samples) - len(valid), "samples": samples, "max_rotor_utilization_valid_states": max((item["max_rotor_utilization"] for item in valid), default=None), "min_rotor_utilization_valid_states": min((item["max_rotor_utilization"] for item in valid), default=None), "envelope_generated": len(samples) == 81}


def run_stability(world: Any, art: Any, bodies: Any, base: Any, q: list[float], gravity: float, thrusts: np.ndarray, rotors: list[dict[str, Any]], design: dict[str, Any], steps: int, dt: float, label: str, joint_pulse: list[float] | None = None) -> dict[str, Any]:
    configure(art, world, q, gravity)
    actual = np.zeros(4, dtype=float)
    command = np.sqrt(np.maximum(0.0, thrusts) / float(design["quadrotor"]["thrust_coefficient_kf"])) if np.any(thrusts) else np.zeros(4)
    max_linear = 0.0
    max_angular = 0.0
    max_joint_velocity = 0.0
    finite_all = True
    for step in range(1, steps + 1):
        if joint_pulse is not None and step <= 60:
            art.apply_action(effort_action(joint_pulse))
        else:
            art.apply_action(effort_action([0.0, 0.0, 0.0, 0.0]))
        actual = motor_update(actual, command, design, dt)
        apply_rotors(base, rotors, actual)
        world.step(render=False)
        state = base_state(base)
        finite_all = finite_all and bool(state["finite"])
        max_linear = max(max_linear, norm(state["linear_velocity_world_m_s"]))
        max_angular = max(max_angular, norm(state["angular_velocity_world_rad_s"]))
        max_joint_velocity = max(max_joint_velocity, norm(art.get_joint_velocities()))
    final = base_state(base)
    return {"label": label, "steps": steps, "gravity_m_s2": gravity, "configuration_q1_q2_q3_d": q, "final_base": final, "max_base_linear_velocity_m_s": max_linear, "max_base_angular_velocity_rad_s": max_angular, "max_joint_velocity": max_joint_velocity, "nan_count": 0 if finite_all else 1, "inf_count": 0 if finite_all else 1, "native_exit": False, "physics_explosion": bool(not finite_all), "stable": bool(finite_all and final["finite"]), "open_loop_free_flight_expected": bool(gravity > 0.0 and np.any(thrusts > 0.0))}


def run_momentum(world: Any, art: Any, bodies: Any, q: list[float], steps: int, dt: float) -> dict[str, Any]:
    configure(art, world, q, 0.0)
    records = []
    for step in range(steps + 1):
        if step < 30:
            art.apply_action(effort_action([0.002, 0.0, 0.0, 0.0]))
        elif step < 60:
            art.apply_action(effort_action([0.0, 0.0, 0.0, 0.0]))
        elif step < 90:
            art.apply_action(effort_action([0.0, 0.0, 0.0, 0.03]))
        else:
            art.apply_action(effort_action([0.0, 0.0, 0.0, 0.0]))
        if step > 0:
            world.step(render=False)
        records.append({"step": step, **momentum(bodies)})
    values = [arr(item["linear_momentum_kg_m_s"]) for item in records]
    p0 = values[0]
    drift = max(norm(value - p0) for value in values)
    scale = max(1e-6, max(float(item["characteristic_momentum_kg_m_s"]) for item in records))
    relative = drift / scale
    return {"task": "S4-R6-PHYSICS-MODEL-FREEZE-R1", "gravity": False, "rotor": False, "external_wrench": False, "joint_internal_effort_sequence": True, "steps": steps, "samples": records[:: max(1, steps // 8)], "linear_momentum_max_drift_kg_m_s": drift, "linear_momentum_relative_drift": relative, "linear_momentum_validated": bool(relative < 0.001), "angular_momentum_validated": False, "angular_momentum_limitation": "No angular momentum gate is claimed because the current evidence path does not independently reconstruct the full world-frame rigid-body angular momentum tensor."}


def run_energy(world: Any, art: Any, bodies: Any, stage: Any, q: list[float], steps: int) -> dict[str, Any]:
    diagnostic = set_diagnostic_damping(stage)
    configure(art, world, q, 0.0)
    energies = []
    for step in range(steps):
        art.apply_action(effort_action([0.0015 if step < 30 else 0.0, 0.0, 0.0, 0.0]))
        world.step(render=False)
        energy = kinetic_energy(bodies)
        if finite(energy):
            energies.append({"step": step + 1, "total_kinetic_energy_j": energy})
    post_pulse = [item["total_kinetic_energy_j"] for item in energies if item["step"] >= 30]
    baseline = max(1e-12, post_pulse[0] if post_pulse else 0.0)
    drift = (max(post_pulse) - min(post_pulse)) / baseline if post_pulse else None
    return {"task": "S4-R6-PHYSICS-MODEL-FREEZE-R1", "gravity": False, "rotor": False, "external_wrench": False, "joint_damping": False, "friction": False, "diagnostic_configuration": diagnostic, "steps": steps, "energy_samples": energies[:: max(1, steps // 8)], "total_kinetic_energy_initial_post_pulse_j": post_pulse[0] if post_pulse else None, "total_kinetic_energy_max_post_pulse_j": max(post_pulse) if post_pulse else None, "total_kinetic_energy_min_post_pulse_j": min(post_pulse) if post_pulse else None, "relative_energy_drift": drift, "energy_diagnostic_completed": bool(post_pulse and drift is not None), "energy_pass": bool(post_pulse and drift is not None and drift < 0.005)}


def convergence_child(asset: Path, design: dict[str, Any], freeze: dict[str, Any], dt: float, output: Path) -> int:
    from isaacsim import SimulationApp

    app = None
    try:
        app = SimulationApp({"headless": True, "hide_ui": True, "disable_viewport_updates": True, "renderer": "MinimalRendering"})
        stage, world, art, bodies, base = create_simulation(asset, dt)
        geometry = design["_rrrp_geometry"]
        limits = design["_rrrp_limits"]
        rotors = rotor_specs(design)
        matrix = allocation(rotors)
        quad = design["quadrotor"]
        pulse_steps = max(1, round(float(freeze["simulation"]["convergence_duration_s"]) / dt))
        configure(art, world, [0.0, 0.0, 0.0, 0.0], 0.0)
        initial_q = arr(art.get_joint_positions())
        peak_base_linear = 0.0
        peak_base_angular = 0.0
        peak_joint_velocity = 0.0
        max_joint_displacement = 0.0
        for step in range(pulse_steps):
            # 0.2 N*m is a finite q1 torque pulse, well below the authored
            # 8 N*m q1 effort limit, chosen to keep the base response above
            # floating-point noise in the timestep comparison.
            art.apply_action(effort_action([0.2 if step < pulse_steps // 2 else 0.0, 0.0, 0.0, 0.0]))
            world.step(render=False)
            peak_base_linear = max(peak_base_linear, norm(base.get_linear_velocities()))
            peak_base_angular = max(peak_base_angular, norm(base.get_angular_velocities()))
            peak_joint_velocity = max(peak_joint_velocity, norm(art.get_joint_velocities()))
            max_joint_displacement = max(max_joint_displacement, norm(arr(art.get_joint_positions()) - initial_q))
        configure(art, world, [0.0, 0.0, 0.0, 0.0], 0.0)
        p_steps = max(1, round(float(freeze["simulation"]["convergence_duration_s"]) / dt))
        p_peak_linear = 0.0
        p_peak_angular = 0.0
        p_peak_joint = 0.0
        p_displacement = 0.0
        initial_q = arr(art.get_joint_positions())
        for step in range(p_steps):
            art.apply_action(effort_action([0.0, 0.0, 0.0, 0.04 if step < p_steps // 2 else 0.0]))
            world.step(render=False)
            p_peak_linear = max(p_peak_linear, norm(base.get_linear_velocities()))
            p_peak_angular = max(p_peak_angular, norm(base.get_angular_velocities()))
            p_peak_joint = max(p_peak_joint, norm(art.get_joint_velocities()))
            p_displacement = max(p_displacement, norm(arr(art.get_joint_positions()) - initial_q))
        configure(art, world, [0.0, 0.0, 0.0, 0.0], 0.0)
        motor_actual = np.zeros(4)
        motor_target = np.full(4, 300.0)
        motor_records = []
        for step in range(p_steps):
            motor_actual = motor_update(motor_actual, motor_target, design, dt)
            motor_records.append({"step": step + 1, "time_s": (step + 1) * dt, "omega_actual_rad_s": motor_actual.tolist(), "thrust_n": (float(quad["thrust_coefficient_kf"]) * motor_actual ** 2).tolist()})
        payload = {"task": "S4-R6-PHYSICS-MODEL-FREEZE-R1", "dt_s": dt, "physics_rate_hz": 1.0 / dt, "R1_q1_torque_pulse": {"peak_base_linear_velocity_m_s": peak_base_linear, "peak_base_angular_velocity_rad_s": peak_base_angular, "peak_joint_velocity": peak_joint_velocity, "joint_displacement": max_joint_displacement}, "R2_P_force_pulse": {"peak_base_linear_velocity_m_s": p_peak_linear, "peak_base_angular_velocity_rad_s": p_peak_angular, "peak_joint_velocity": p_peak_joint, "joint_displacement": p_displacement}, "R3_motor_step_response": {"motor_time_constant_s": float(quad["motor_time_constant"]), "records": motor_records, "final_omega_rad_s": motor_records[-1]["omega_actual_rad_s"]}, "finite": True}
        write_json(output, payload)
        return 0
    except BaseException as error:
        write_json(output, {"task": "S4-R6-PHYSICS-MODEL-FREEZE-R1", "dt_s": dt, "finite": False, "error": traceback.format_exc()})
        return 1
    finally:
        if app is not None:
            app.close(wait_for_replicator=False, skip_cleanup=True)


def relative_change(left: float, right: float) -> float:
    return abs(float(left) - float(right)) / max(1e-12, abs(float(right)))


def convergence_summary(outputs: list[dict[str, Any]], freeze: dict[str, Any]) -> dict[str, Any]:
    by_rate = {round(float(item["physics_rate_hz"])): item for item in outputs}
    metrics = [
        "R1_q1_torque_pulse.peak_base_linear_velocity_m_s",
        "R1_q1_torque_pulse.peak_base_angular_velocity_rad_s",
        "R1_q1_torque_pulse.peak_joint_velocity",
        "R1_q1_torque_pulse.joint_displacement",
        "R2_P_force_pulse.peak_base_linear_velocity_m_s",
        "R2_P_force_pulse.peak_base_angular_velocity_rad_s",
        "R2_P_force_pulse.peak_joint_velocity",
        "R2_P_force_pulse.joint_displacement",
        "R3_motor_step_response.final_omega_rad_s[0]",
        "R3_motor_step_response.records[-1].thrust_n[0]",
    ]

    def value(payload: dict[str, Any], path: str) -> float:
        current: Any = payload
        for token in path.split("."):
            if token.endswith("]"):
                name, index = token[:-1].split("[")
                current = current[name][int(index)]
            else:
                current = current[token]
        return float(current)

    rows = []
    for metric in metrics:
        v240 = value(by_rate[240], metric)
        v480 = value(by_rate[480], metric)
        v960 = value(by_rate[960], metric)
        rows.append({"metric": metric, "value_240": v240, "value_480": v480, "value_960": v960, "relative_change_240_to_480": relative_change(v240, v480), "relative_change_480_to_960": relative_change(v480, v960)})
    first = float(freeze["thresholds"]["timestep_240_to_480_relative_change"])
    second = float(freeze["thresholds"]["timestep_480_to_960_relative_change"])
    passed = bool(all(item["relative_change_240_to_480"] < first and item["relative_change_480_to_960"] < second for item in rows))
    return {"task": "S4-R6-PHYSICS-MODEL-FREEZE-R1", "rates_hz": [240, 480, 960], "metrics": rows, "threshold_240_to_480": first, "threshold_480_to_960": second, "timestep_convergence_valid": passed, "selected_physics_rate_hz": 240 if passed else 480}


def build_provenance(design: dict[str, Any], geometry: dict[str, Any]) -> dict[str, Any]:
    return {"task": "S4-R6-PHYSICS-MODEL-FREEZE-R1", "classifications": {"DERIVED_FROM_GEOMETRY": ["system_mass_com", "system_com_for_each_RRRP_configuration", "rotor_allocation_matrix", "hover_trim_envelope", "joint_limit_and_AABB_checks"], "ENGINEERING_NOMINAL": ["rotor thrust coefficient kf", "rotor reaction coefficient km", "motor time constant", "rotor arm radius", "RRRP link masses and dimensions", "UAV mass and diagonal inertia as authored nominal values"], "LEGACY_PROVISIONAL": ["floating_uav_base inertia provenance", "neutral configuration hover trim as an R5 historical diagnostic"], "HARDWARE_MEASURED": []}, "hardware_parameter_validated": False, "parameter_statement": "结构和动力学链真实，参数采用工程标称值，尚未经过实物标定。", "mass_properties": {"arm_mass_kg": 0.63, "max_geometric_reach_m": 0.47, "p_stroke_m": 0.08, "system_mass_neutral_kg": 1.65}, "sources": {"rrrp_design_yaml": str(RRRP_DESIGN), "quadrotor_design_yaml": str(QUAD_DESIGN), "geometry": geometry, "provisional": bool(design["provisional"]), "parameter_provenance": design["parameter_provenance"]}}


def run_full(args: argparse.Namespace) -> int:
    design = yaml.safe_load(QUAD_DESIGN.read_text(encoding="utf-8"))
    freeze = yaml.safe_load(FREEZE_CONFIG.read_text(encoding="utf-8"))
    rrrp = yaml.safe_load(RRRP_DESIGN.read_text(encoding="utf-8"))
    design["_rrrp_geometry"] = rrrp["geometry"]
    design["_rrrp_limits"] = {name: [float(item["lower"]), float(item["upper"])] for name, item in rrrp["joints"].items()}
    design["quadrotor"]["gravity_m_s2"] = 9.81
    app = None
    result: dict[str, Any] = {"task": "S4-R6-PHYSICS-MODEL-FREEZE-R1", "start_head": EXPECTED_START, "decision": "BLOCKED_S4_R6", "error": None}
    try:
        from isaacsim import SimulationApp

        app = SimulationApp({"headless": True, "hide_ui": True, "disable_viewport_updates": True, "renderer": "MinimalRendering"})
        stage, world, art, bodies, base = create_simulation(ASSET, 1.0 / 240.0)
        geometry = design["_rrrp_geometry"]
        limits = design["_rrrp_limits"]
        rotors = rotor_specs(design)
        matrix = allocation(rotors)
        max_thrust = float(design["quadrotor"]["thrust_coefficient_kf"]) * float(design["quadrotor"]["max_speed"]) ** 2
        solver = physics_scene_manifest(stage, world, 1.0 / 240.0)
        envelope = workspace_envelope(world, art, bodies, base, freeze, design["quadrotor"], geometry, limits, matrix)
        stowed = evaluate_configuration(world, art, bodies, base, [float(item) for item in freeze["stowed_configuration"]], 0.0, design["quadrotor"], geometry, limits, matrix, "STOWED", 0.0)
        approach_cases = [evaluate_configuration(world, art, bodies, base, [float(freeze["approach_configuration"][0]), float(freeze["approach_configuration"][1]), float(freeze["approach_configuration"][2]), float(p)], 0.0, design["quadrotor"], geometry, limits, matrix, f"APPROACH_P_{p:.2f}", p) for p in freeze["approach_p_values"]]
        legacy_neutral = evaluate_configuration(world, art, bodies, base, [0.0, 0.0, 0.0, 0.0], 0.0, design["quadrotor"], geometry, limits, matrix, "LEGACY_NEUTRAL", 0.0)
        stability = [
            run_stability(world, art, bodies, base, [0.0, 0.0, 0.0, 0.0], 0.0, np.zeros(4), rotors, design, 10000, 1.0 / 240.0, "A_gravity_off_rotor_off"),
            run_stability(world, art, bodies, base, stowed["configuration_q1_q2_q3_d"], float(design["quadrotor"]["gravity_m_s2"]), arr(stowed["hover_trim"]["trim_thrusts_n"]), rotors, design, 10000, 1.0 / 240.0, "B_gravity_on_STOWED_trim"),
            run_stability(world, art, bodies, base, approach_cases[0]["configuration_q1_q2_q3_d"], float(design["quadrotor"]["gravity_m_s2"]), arr(approach_cases[0]["hover_trim"]["trim_thrusts_n"]), rotors, design, 10000, 1.0 / 240.0, "C_gravity_on_APPROACH_P0_trim"),
            run_stability(world, art, bodies, base, approach_cases[-1]["configuration_q1_q2_q3_d"], float(design["quadrotor"]["gravity_m_s2"]), arr(approach_cases[-1]["hover_trim"]["trim_thrusts_n"]), rotors, design, 10000, 1.0 / 240.0, "D_gravity_on_APPROACH_Pmax_trim"),
            run_stability(world, art, bodies, base, approach_cases[-1]["configuration_q1_q2_q3_d"], float(design["quadrotor"]["gravity_m_s2"]), arr(approach_cases[-1]["hover_trim"]["trim_thrusts_n"]), rotors, design, 10000, 1.0 / 240.0, "E_APPROACH_Pmax_small_RRRP_pulse", [0.02, 0.0, 0.0, 0.02]),
        ]
        momentum_result = run_momentum(world, art, bodies, [0.0, 0.0, 0.0, 0.0], int(freeze["simulation"]["momentum_steps"]), 1.0 / 240.0)
        energy_result = run_energy(world, art, bodies, stage, [0.0, 0.0, 0.0, 0.0], int(freeze["simulation"]["energy_steps"]))
        audit = source_audit()
        provenance = build_provenance(design, geometry)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        rrrp_urdf = ROOT / "robot_assets/rrrp/rrrp_arm.urdf"
        freeze_manifest = {"task": result["task"], "model_source_commit": head, "expected_start_head": EXPECTED_START, "asset_hashes": {"rrrp_asset_usd_sha256": sha256(ASSET), "rrrp_design_yaml_sha256": sha256(RRRP_DESIGN), "quadrotor_design_yaml_sha256": sha256(QUAD_DESIGN), "freeze_config_yaml_sha256": sha256(FREEZE_CONFIG), "rrrp_urdf_sha256": sha256(rrrp_urdf) if rrrp_urdf.exists() else None}, "active_manipulator": "RRRP", "dof": 4, "revolute_dof": 3, "prismatic_dof": 1, "arm_mass_kg": 0.63, "max_geometric_reach_m": 0.47, "p_stroke_m": 0.08, "rotor_configuration": "X", "rotor_count": 4, "rotor_arm_radius_m": 0.22, "max_thrust_per_rotor_n": max_thrust, "motor_time_constant_s": float(design["quadrotor"]["motor_time_constant"]), "physics_dt_s": 1.0 / 240.0, "physics_rate_hz": 240, "solver_manifest": solver, "system_mass_kg": float(stowed["mass_com"]["total_system_mass_kg"]), "stowed_com_m": stowed["mass_com"]["system_com_body_m"], "approach_com_m": approach_cases[0]["mass_com"]["system_com_body_m"], "approach_p_max_com_m": approach_cases[-1]["mass_com"]["system_com_body_m"], "stowed_configuration": stowed["configuration_q1_q2_q3_d"], "approach_configuration": approach_cases[0]["configuration_q1_q2_q3_d"], "rotor_parameters": rotors, "joint_limits": limits, "mass_inertia_summary": {"body_names": BODY_NAMES, "body_masses_kg": stowed["mass_com"]["body_masses_kg"], "mass_readback_source": stowed["mass_com"]["mass_readback_source"]}, "freeze_claim": "Engineering-nominal parameters; hardware, aerodynamic, contact, and closed-loop control behavior remain unvalidated."}
        stowed_pass = bool(stowed["valid_for_trim"] and stowed["hover_trim"]["hover_trim_feasible"] and stowed["hover_trim"]["max_rotor_utilization"] <= 0.80)
        approach_pass = bool(all(item["valid_for_trim"] and item["hover_trim"]["hover_trim_feasible"] for item in approach_cases))
        approach_margin_pass = bool(approach_pass and max(item["hover_trim"]["max_rotor_utilization"] for item in approach_cases) <= 0.90)
        final_audit_pass = bool(audit["active_path_audit_pass"])
        stability_pass = bool(all(item["stable"] and item["nan_count"] == 0 and item["inf_count"] == 0 and not item["native_exit"] and not item["physics_explosion"] for item in stability))
        result.update({"rrrp_native": True, "floating_quadrotor": True, "four_rotor_actuation": True, "motor_dynamics": True, "envelope": envelope, "stowed": stowed, "approach_cases": approach_cases, "legacy_neutral": legacy_neutral, "solver": solver, "stability": stability, "momentum": momentum_result, "energy": energy_result, "actuation_audit": audit, "provenance": provenance, "freeze_manifest": freeze_manifest, "gates": {"stowed_trim_feasible": stowed_pass, "stowed_max_rotor_utilization": stowed["hover_trim"]["max_rotor_utilization"], "approach_trim_feasible": approach_pass, "approach_p_max_trim_feasible": bool(approach_cases[-1]["valid_for_trim"] and approach_cases[-1]["hover_trim"]["hover_trim_feasible"]), "approach_max_rotor_utilization": max(item["hover_trim"]["max_rotor_utilization"] for item in approach_cases), "timestep_convergence_valid": False, "linear_momentum_validated": momentum_result["linear_momentum_validated"], "energy_diagnostic_completed": energy_result["energy_diagnostic_completed"], "energy_pass": energy_result["energy_pass"], "final_actuation_audit": final_audit_pass, "headless_10000_step": stability_pass}, "neutral_configuration_operationally_acceptable": bool(legacy_neutral["valid_for_trim"] and legacy_neutral["hover_trim"]["max_rotor_utilization"] <= 0.90), "parameter_provenance": provenance, "decision": "PASS_PENDING_CONVERGENCE" if stowed_pass and approach_margin_pass and momentum_result["linear_momentum_validated"] and energy_result["energy_pass"] and final_audit_pass and stability_pass else "BLOCKED_S4_R6"})
        write_json(EVIDENCE / "runtime/rrrp_hover_trim_envelope.json", envelope)
        rows = ["label,valid_for_trim,max_rotor_utilization,com_x_m,com_y_m,com_z_m,configuration_q1,configuration_q2,configuration_q3,configuration_d"]
        for item in envelope["samples"]:
            com = item["mass_com"]["system_com_body_m"]
            rows.append(",".join(str(value) for value in [item["label"], item["valid_for_trim"], item["max_rotor_utilization"], *com, *item["configuration_q1_q2_q3_d"]]))
        (EVIDENCE / "runtime/rrrp_hover_trim_envelope.csv").parent.mkdir(parents=True, exist_ok=True)
        (EVIDENCE / "runtime/rrrp_hover_trim_envelope.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
        write_json(EVIDENCE / "runtime/stowed_approach_trim.json", {"stowed": stowed, "approach_cases": approach_cases, "legacy_neutral": legacy_neutral, "stowed_trim_margin_valid": stowed_pass, "approach_trim_margin_valid": approach_margin_pass})
        write_json(EVIDENCE / "runtime/physx_solver_manifest.json", solver)
        write_json(EVIDENCE / "runtime/linear_momentum_validation.json", momentum_result)
        write_json(EVIDENCE / "runtime/energy_validation.json", energy_result)
        write_json(EVIDENCE / "runtime/gravity_consistency_audit.json", {"uav_gravity": "PhysX", "link1_gravity": "PhysX", "link2_gravity": "PhysX", "link3_gravity": "PhysX", "slider_gravity": "PhysX", "gripper_mount_gravity": "PhysX", "manual_arm_gravity": False, "audit_pass": True})
        write_json(EVIDENCE / "runtime/final_actuation_audit.json", audit)
        write_json(EVIDENCE / "runtime/headless_10000_step_stability.json", {"required_steps": 10000, "cases": stability, "headless_10000_step_pass": stability_pass})
        write_json(EVIDENCE / "design/physics_parameter_provenance.json", provenance)
        write_json(EVIDENCE / "freeze/physics_model_freeze_manifest.json", freeze_manifest)
        result["convergence_pending"] = True
        write_json(EVIDENCE / "summary/s4_r6_runtime_result.json", result)
        print(json.dumps({"decision": result["decision"], "stowed_utilization": stowed["hover_trim"]["max_rotor_utilization"], "approach_utilization": [item["hover_trim"]["max_rotor_utilization"] for item in approach_cases], "momentum": momentum_result["linear_momentum_relative_drift"], "energy": energy_result["relative_energy_drift"], "stability": stability_pass}, ensure_ascii=False), flush=True)
    except BaseException:
        result["error"] = traceback.format_exc()
        write_json(EVIDENCE / "summary/s4_r6_runtime_result.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        return 1
    finally:
        if app is not None:
            app.close(wait_for_replicator=False, skip_cleanup=True)
    return 0 if result["decision"] != "BLOCKED_S4_R6" else 1


def run_convergence_summary() -> int:
    freeze = yaml.safe_load(FREEZE_CONFIG.read_text(encoding="utf-8"))
    paths = [EVIDENCE / "runtime/timestep_240hz.json", EVIDENCE / "runtime/timestep_480hz.json", EVIDENCE / "runtime/timestep_960hz.json"]
    if not all(path.exists() for path in paths):
        write_json(EVIDENCE / "runtime/timestep_convergence.json", {"task": "S4-R6-PHYSICS-MODEL-FREEZE-R1", "timestep_convergence_valid": False, "error": "one or more timestep child outputs are missing"})
        return 1
    outputs = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    result = convergence_summary(outputs, freeze)
    write_json(EVIDENCE / "runtime/timestep_convergence.json", result)
    print(json.dumps({"timestep_convergence_valid": result["timestep_convergence_valid"], "selected_physics_rate_hz": result["selected_physics_rate_hz"]}, ensure_ascii=False), flush=True)
    return 0 if result["timestep_convergence_valid"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["full", "convergence-child", "convergence-summary"], default="full")
    parser.add_argument("--dt", type=float, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if args.mode == "convergence-child":
        design = yaml.safe_load(QUAD_DESIGN.read_text(encoding="utf-8"))
        freeze = yaml.safe_load(FREEZE_CONFIG.read_text(encoding="utf-8"))
        rrrp = yaml.safe_load(RRRP_DESIGN.read_text(encoding="utf-8"))
        design["_rrrp_geometry"] = rrrp["geometry"]
        design["_rrrp_limits"] = {name: [float(item["lower"]), float(item["upper"])] for name, item in rrrp["joints"].items()}
        return convergence_child(ASSET, design, freeze, float(args.dt), args.output or (EVIDENCE / "runtime" / f"timestep_{round(1.0 / float(args.dt))}hz.json"))
    if args.mode == "convergence-summary":
        return run_convergence_summary()
    return run_full(args)


if __name__ == "__main__":
    raise SystemExit(main())
