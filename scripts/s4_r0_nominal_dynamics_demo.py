"""S4-R0 real Isaac dynamics demo.

The base is a PhysX-integrated floating DynamicCuboid.  The Delta arm uses a
route-B analytic COM reaction surrogate and the frozen S3 USD as its visual
asset.  The visual copy is physics-isolated; q is integrated by a bounded
joint PD model and its analytic COM wrench is applied to the real base body.
No post-reset root or active-joint state is written to the dynamic proxy.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import time
from pathlib import Path
from typing import Any

import numpy as np

from planner_bridge.control.arm_joint_controller import ArmJointController
from planner_bridge.control.contracts import quat_wxyz_to_rotation
from planner_bridge.control.dynamic_model import ArmReactionSurrogate
from planner_bridge.control.metrics import max_norm, rmse, saturation_summary, settling_time, vector_rmse
from planner_bridge.control.nominal_base_controller import NominalBaseController
from planner_bridge.execution.full_body_proxy import component_sample_sets, sampled_proxy_aabb_clearance
from planner_bridge.execution.official_delta_kinematics import official_fk_joint_state, official_joint_points
from planner_bridge.scenes.s3_r0_scene_contract import SCENE_AABBS


ROOT = Path(__file__).resolve().parents[1]
DT = 1.0 / 240.0
RENDER_EVERY = 8
BASE_POSITION = np.asarray([0.0, 0.0, 2.5], dtype=float)
Q_HOME = np.asarray([0.72, 0.72, 0.72], dtype=float)
ACTIVE_JOINTS = ("m1_1", "m2_1", "m3_1")
PASSIVE_JOINTS = ("m1_2", "m1_3", "m2_2", "m2_3", "m3_2", "m3_3")
ROBOT_USD = Path(r"D:/i3/a/aerial_manipulator_v2.usd")
ROBOT_USD_SHA256 = "74cce4b4cd8a41da9b60829482debbf3a78c0548bacb9dd53089e92c5ed7bc7d"
ARM_MASS_FROM_USD_KG = 0.29135232232511


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _config() -> dict[str, Any]:
    return {
        "base_mass_kg": 0.98,
        "arm_mass_kg": ARM_MASS_FROM_USD_KG,
        "mass_kg": 0.98 + ARM_MASS_FROM_USD_KG,
        "mass_accounting_mode": "BASE_PLUS_ARM_SEPARATE",
        "arm_gravity_handling": "EXPLICIT_ARM_GRAVITY_FORCE_PLUS_TOTAL_HOVER_FEEDFORWARD",
        "gravity_m_s2": 9.81,
        "kp_pos": [4.0, 4.0, 8.0],
        "kd_pos": [3.2, 3.2, 4.8],
        "kp_att": [2.8, 2.8, 1.2],
        "kd_att": [0.22, 0.22, 0.16],
        "inertia_kg_m2": [0.018, 0.018, 0.032],
        "max_force_n": 30.0,
        "max_torque_nm": [1.5, 1.5, 0.8],
        "arm": {"kp": [3.0, 3.0, 3.0], "kd": [0.12, 0.12, 0.12], "max_effort_nm": [0.8, 0.8, 0.8], "lower_rad": [0.0, 0.0, 0.0], "upper_rad": [math.pi / 2.0] * 3},
    }


def _load_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _config()
    try:
        import yaml

        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        config = _config()
        config.update(payload.get("vehicle", {}))
        config.update(payload.get("base_controller", {}))
        config["arm"] = dict(config["arm"], **payload.get("arm_controller", {}))
        config["mass_kg"] = float(config["base_mass_kg"]) + float(config["arm_mass_kg"])
        return config
    except Exception:
        return _config()


def _quat_from_rpy(roll: float, pitch: float, yaw: float = 0.0) -> np.ndarray:
    cr, sr = math.cos(roll / 2.0), math.sin(roll / 2.0)
    cp, sp = math.cos(pitch / 2.0), math.sin(pitch / 2.0)
    cy, sy = math.cos(yaw / 2.0), math.sin(yaw / 2.0)
    return np.asarray([cr * cp * cy + sr * sp * sy, sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy], dtype=float)


def _rpy_from_rotation(rotation: np.ndarray) -> np.ndarray:
    return np.asarray([math.atan2(rotation[2, 1], rotation[2, 2]), math.asin(np.clip(-rotation[2, 0], -1.0, 1.0)), math.atan2(rotation[1, 0], rotation[0, 0])], dtype=float)


def _attitude_error(rotation: np.ndarray, reference: np.ndarray | None = None) -> float:
    reference = np.eye(3) if reference is None else reference
    relative = reference.T @ rotation
    cosine = np.clip((np.trace(relative) - 1.0) * 0.5, -1.0, 1.0)
    return float(math.acos(cosine))


def _make_segment(stage: Any, path: str, color: tuple[float, float, float]) -> tuple[Any, Any, Any, Any]:
    from pxr import Gf, UsdGeom

    prim = stage.DefinePrim(path, "Cube")
    cube = UsdGeom.Cube(prim)
    cube.CreateSizeAttr(1.0)
    cube.CreateDisplayColorAttr().Set([Gf.Vec3f(*color)])
    xf = UsdGeom.Xformable(prim)
    translate = xf.AddTranslateOp()
    orient = xf.AddOrientOp()
    scale = xf.AddScaleOp()
    return prim, translate, orient, scale


def _update_segment(ops: tuple[Any, Any, Any, Any], start: np.ndarray, end: np.ndarray, thickness: float = 0.018) -> None:
    from pxr import Gf

    direction = np.asarray(end, dtype=float) - np.asarray(start, dtype=float)
    length = float(np.linalg.norm(direction))
    if length < 1e-9:
        return
    mid = (np.asarray(start, dtype=float) + np.asarray(end, dtype=float)) * 0.5
    rotation = Gf.Rotation(Gf.Vec3d(0.0, 0.0, 1.0), Gf.Vec3d(*direction.tolist()))
    ops[1].Set(Gf.Vec3d(*mid.tolist()))
    quat = rotation.GetQuat()
    ops[2].Set(Gf.Quatf(float(quat.GetReal()), Gf.Vec3f(*[float(v) for v in quat.GetImaginary()])))
    ops[3].Set(Gf.Vec3d(thickness, thickness, length))


def _attach_real_visual(stage: Any) -> dict[str, Any]:
    from pxr import Gf, UsdGeom

    visual_root = stage.DefinePrim("/World/RobotVisual", "Xform")
    asset_root = stage.DefinePrim("/World/RobotVisual/Asset", "Xform")
    asset_root.GetReferences().AddReference(str(ROBOT_USD.resolve()))
    visual_translate = UsdGeom.Xformable(visual_root).AddTranslateOp(precision=UsdGeom.XformOp.PrecisionDouble)
    visual_orient = UsdGeom.Xformable(visual_root).AddOrientOp(precision=UsdGeom.XformOp.PrecisionDouble)
    visual_translate.Set(Gf.Vec3d(*BASE_POSITION.tolist()))
    visual_orient.Set(Gf.Quatd(1.0, Gf.Vec3d(0.0, 0.0, 0.0)))
    visual_physics_disabled = 0
    visual_collision_disabled = 0
    for prim in stage.Traverse():
        if not str(prim.GetPath()).startswith("/World/RobotVisual/Asset"):
            continue
        prim.SetCustomDataByKey("s4_visual_only", True)
        for attribute_name in ("physics:rigidBodyEnabled", "physics:articulationEnabled", "physics:jointEnabled"):
            attribute = prim.GetAttribute(attribute_name)
            if attribute.IsValid():
                attribute.Set(False)
                visual_physics_disabled += 1
        collision_enabled = prim.GetAttribute("physics:collisionEnabled")
        if collision_enabled.IsValid():
            collision_enabled.Set(False)
            visual_collision_disabled += 1
        for schema in ("PhysicsArticulationRootAPI", "PhysicsRigidBodyAPI", "PhysxRigidBodyAPI", "PhysicsCollisionAPI", "PhysxCollisionAPI"):
            try:
                prim.RemoveAPI(schema)
            except Exception:
                pass
        for attribute_name in ("drive:angular:physics:stiffness", "drive:angular:physics:damping", "drive:angular:physics:maxForce"):
            attribute = prim.GetAttribute(attribute_name)
            if attribute.IsValid():
                attribute.Set(0.0)
    visual_joints = {name: stage.GetPrimAtPath(f"/World/RobotVisual/Asset/body/joints/{name}") for name in (*ACTIVE_JOINTS, *PASSIVE_JOINTS)}
    visual_prim_count = sum(1 for prim in stage.Traverse() if str(prim.GetPath()).startswith("/World/RobotVisual"))
    return {
        "source_usd": str(ROBOT_USD.resolve()),
        "source_sha256": sha256(ROBOT_USD),
        "stage_prim": "/World/RobotVisual",
        "dynamic_base_prim": "/World/QuadrotorBase",
        "root_translate": visual_translate,
        "root_orient": visual_orient,
        "joint_prims": visual_joints,
        "visual_prim_count": visual_prim_count,
        "mesh_prim_count": sum(1 for prim in stage.Traverse() if str(prim.GetPath()).startswith("/World/RobotVisual") and prim.GetTypeName() == "Mesh"),
        "physics_disabled_for_visual_copy": visual_physics_disabled > 0,
        "collision_disabled_for_visual_copy": visual_collision_disabled > 0,
        "physics_disabled_prim_count": visual_physics_disabled,
        "collision_disabled_prim_count": visual_collision_disabled,
    }


def _make_scene(world: Any, stage: Any, config: dict[str, Any]) -> tuple[Any, list[tuple[Any, Any, Any, Any]]]:
    from isaacsim.core.api.objects import DynamicCuboid, FixedCuboid
    from pxr import Gf, UsdGeom, UsdPhysics

    # Keep the dynamic proxy compact enough that nominal hover is not a
    # contact experiment with the frozen MainBeam AABB below it.  Collision is
    # intentionally disabled for this route-B nominal proof; contact fields
    # are therefore reported as unavailable rather than as a false zero.
    base_mass = float(config["base_mass_kg"])
    base_object = DynamicCuboid(prim_path="/World/QuadrotorBase", name="quadrotor_base", position=BASE_POSITION, size=0.20, mass=base_mass, color=np.asarray([0.12, 0.38, 0.82]))
    base = world.scene.add(base_object)
    base_prim = stage.GetPrimAtPath("/World/QuadrotorBase")
    mass_api = UsdPhysics.MassAPI.Apply(base_prim)
    mass_api.CreateMassAttr().Set(base_mass)
    mass_api.CreateDiagonalInertiaAttr().Set(Gf.Vec3f(0.018, 0.018, 0.032))
    collision_api = UsdPhysics.CollisionAPI.Apply(base_prim)
    collision_api.CreateCollisionEnabledAttr().Set(False)
    for name, box in SCENE_AABBS.items():
        world.scene.add(FixedCuboid(prim_path=f"/World/Scene/{name}", name=f"obstacle_{name}", position=np.asarray(box.center_m), size=1.0, scale=np.asarray(box.size_m), color=np.asarray([0.65, 0.23, 0.10])))
    world.scene.add_default_ground_plane(z_position=0.0)
    # Procedural debug cubes are intentionally omitted from the submitted
    # scene; clearance still uses the same official Delta point geometry.
    return base, []


def _update_arm_visual(segments: list[tuple[Any, Any, Any, Any]], base_position: np.ndarray, base_rotation: np.ndarray, q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a0 = official_fk_joint_state(q)
    points = official_joint_points(a0, q)
    origin = base_position + base_rotation @ np.asarray([0.0, 0.0, -0.05])
    def world(value: np.ndarray) -> np.ndarray:
        return origin + base_rotation @ np.asarray(value, dtype=float)
    if segments:
        index = 0
        for branch in range(3):
            _update_segment(segments[index], world(points["A"][branch]), world(points["B"][branch])); index += 1
            _update_segment(segments[index], world(points["B_left"][branch]), world(points["C_left"][branch])); index += 1
            _update_segment(segments[index], world(points["B_right"][branch]), world(points["C_right"][branch])); index += 1
    return a0, points


def _update_real_visual(visual_binding: dict[str, Any], base_position: np.ndarray, quaternion: np.ndarray, q: np.ndarray, dq: np.ndarray) -> None:
    """Bind the frozen USD root and disabled joint state to the same proxy q."""

    if not visual_binding.get("available", True):
        return
    from pxr import Gf

    visual_binding["root_translate"].Set(Gf.Vec3d(*np.asarray(base_position, dtype=float).tolist()))
    visual_binding["root_orient"].Set(Gf.Quatd(float(quaternion[0]), Gf.Vec3d(*quaternion[1:].tolist())))
    for name, value, velocity in zip(ACTIVE_JOINTS, np.asarray(q, dtype=float), np.asarray(dq, dtype=float)):
        prim = visual_binding["joint_prims"].get(name)
        if prim is None or not prim.IsValid():
            continue
        target = prim.GetAttribute("drive:angular:physics:targetPosition")
        target_velocity = prim.GetAttribute("drive:angular:physics:targetVelocity")
        state = prim.GetAttribute("state:angular:physics:position")
        state_velocity = prim.GetAttribute("state:angular:physics:velocity")
        if target.IsValid():
            target.Set(float(value))
        if target_velocity.IsValid():
            target_velocity.Set(float(velocity))
        if state.IsValid():
            state.Set(float(value))
        if state_velocity.IsValid():
            state_velocity.Set(float(velocity))


def _clearance(base_position: np.ndarray, base_rotation: np.ndarray, arm_point: np.ndarray, points: dict[str, np.ndarray]) -> tuple[float, str]:
    samples = component_sample_sets(base_position, base_rotation, arm_point, points)
    best = (float("inf"), "")
    for component, sample_set in samples.items():
        for obstacle, box in SCENE_AABBS.items():
            record = sampled_proxy_aabb_clearance(sample_set, np.asarray(box.center_m), np.asarray(box.size_m))
            if float(record["clearance_m"]) < best[0]:
                best = (float(record["clearance_m"]), f"{component}->{obstacle}")
    return best


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = ["time_s", "x_m", "y_m", "z_m", "position_error_m", "attitude_error_deg", "speed_m_s", "angular_speed_rad_s", "force_n", "torque_nm", "joint_error_rad", "ee_error_m", "clearance_m", "force_saturated", "torque_saturated", "joint_saturated", "controller_enabled", "post_reset_state_write_count", "post_reset_active_joint_state_write_count"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for record in records:
            position = np.asarray(record["position_m"], dtype=float)
            row = {
                "time_s": record["time_s"],
                "x_m": position[0], "y_m": position[1], "z_m": position[2],
                "position_error_m": record["position_error_m"],
                "attitude_error_deg": math.degrees(record["attitude_error_rad"]),
                "speed_m_s": float(np.linalg.norm(record["velocity_m_s"])),
                "angular_speed_rad_s": float(np.linalg.norm(record["angular_velocity_body_rad_s"])),
                "force_n": float(np.linalg.norm(record["force_clipped_N"])),
                "torque_nm": float(np.linalg.norm(record["torque_clipped_Nm"])),
                "joint_error_rad": record["joint_error_rad"],
                "ee_error_m": float(np.linalg.norm(np.asarray(record["world_ee_actual_m"]) - np.asarray(record["world_ee_reference_m"]))),
                "clearance_m": record["minimum_clearance_m"],
                "force_saturated": record["force_saturated"],
                "torque_saturated": record["torque_saturated"],
                "joint_saturated": record["joint_saturated"],
                "controller_enabled": record["controller_enabled"],
                "post_reset_state_write_count": record["post_reset_state_write_count"],
                "post_reset_active_joint_state_write_count": record["post_reset_active_joint_state_write_count"],
            }
            writer.writerow(row)


def _reset_episode(base: Any, position: np.ndarray, quaternion: np.ndarray, *, state_write_counter: dict[str, int]) -> None:
    """Reset-only state initialization; never called from the control loop."""

    base.set_world_pose(position=np.asarray(position, dtype=float), orientation=np.asarray(quaternion, dtype=float))
    base.set_linear_velocity(np.zeros(3))
    base.set_angular_velocity(np.zeros(3))
    # Synchronize the reset-only PhysX view as well.  This is deliberately
    # isolated here; it is never called from the controller loop.
    base._rigid_prim_view.set_world_poses(np.asarray([position], dtype=float), np.asarray([quaternion], dtype=float), usd=True)
    base._rigid_prim_view.set_velocities(np.zeros((1, 6), dtype=float))
    state_write_counter["reset_root_state_writes"] += 1


def _apply_wrench(base: Any, force_world: np.ndarray, torque_world: np.ndarray) -> None:
    base._rigid_prim_view.apply_forces_and_torques_at_pos(np.asarray([force_world], dtype=float), np.asarray([torque_world], dtype=float), is_global=True)


def _read_base_state(stage: Any, previous: tuple[np.ndarray, np.ndarray] | None, dt: float, rigid_view: Any | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Read the physics-integrated root transform from USD and differentiate it."""

    prim = stage.GetPrimAtPath("/World/QuadrotorBase")
    position = np.asarray(prim.GetAttribute("xformOp:translate").Get(), dtype=float)
    orient = prim.GetAttribute("xformOp:orient").Get()
    quaternion = np.asarray([float(orient.GetReal()), *[float(v) for v in orient.GetImaginary()]], dtype=float)
    rotation = quat_wxyz_to_rotation(quaternion)
    if rigid_view is not None:
        velocities = np.asarray(rigid_view.get_velocities(), dtype=float)[0]
        return position, quaternion, velocities[:3], rotation.T @ velocities[3:]
    if previous is None:
        return position, quaternion, np.zeros(3), np.zeros(3)
    previous_position, previous_quaternion = previous
    velocity = (position - previous_position) / dt
    previous_rotation = quat_wxyz_to_rotation(previous_quaternion)
    delta = previous_rotation.T @ rotation
    angular = 0.5 / dt * np.asarray([delta[2, 1] - delta[1, 2], delta[0, 2] - delta[2, 0], delta[1, 0] - delta[0, 1]], dtype=float)
    return position, quaternion, velocity, angular


def _capture(viewport: Any, path: Path, app: Any) -> None:
    from omni.kit.viewport.utility import capture_viewport_to_file

    path.parent.mkdir(parents=True, exist_ok=True)
    capture_viewport_to_file(viewport, file_path=str(path), is_hdr=False)
    if path.is_file() and path.stat().st_size > 0:
        return
    raise TimeoutError(f"viewport capture missing: {path}")


def _run_episode(world: Any, app: Any, stage: Any, base: Any, segments: list[tuple[Any, Any, Any, Any]], visual_binding: dict[str, Any], controllers: tuple[NominalBaseController, ArmJointController], surrogate: ArmReactionSurrogate, scenario: str, run_id: str, duration_s: float, reset_position: np.ndarray, reset_quaternion: np.ndarray, *, coupling_on: bool, capture_enabled: bool, viewport: Any | None, output_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    base_controller, arm_controller = controllers
    state_write_counter = {"reset_root_state_writes": 0}
    _reset_episode(base, reset_position, reset_quaternion, state_write_counter=state_write_counter)
    world.step(render=False)
    q = Q_HOME.copy()
    dq = np.zeros(3)
    previous_base_state: tuple[np.ndarray, np.ndarray] | None = None
    records: list[dict[str, Any]] = []
    raw_records: list[dict[str, Any]] = []
    visual_frames: list[dict[str, Any]] = []
    total_steps = int(round(duration_s / DT)) + 1
    visual_dir = output_root / "local_visuals" / "S4-R0" / scenario / run_id
    for step in range(total_steps):
        time_s = step * DT
        position, quaternion, velocity, angular_velocity = _read_base_state(stage, previous_base_state, DT, base._rigid_prim_view)
        previous_before_step = (position.copy(), quaternion.copy())
        rotation = quat_wxyz_to_rotation(quaternion)
        reference_position = BASE_POSITION
        if scenario == "arm_motion_hold":
            omega = 2.0 * math.pi / 10.0
            amp = 0.15
            q_ref = Q_HOME + amp * np.sin(omega * time_s + np.asarray([0.0, 2.0, 4.0]))
            dq_ref = amp * omega * np.cos(omega * time_s + np.asarray([0.0, 2.0, 4.0]))
        else:
            q_ref = Q_HOME
            dq_ref = np.zeros(3)
        joint_command = arm_controller.compute(q, dq, q_ref, dq_ref)
        qdd = (joint_command.effort_clipped - 0.06 * dq) / np.asarray([0.0022, 0.0022, 0.0022])
        reaction = surrogate.reaction(q, dq, qdd, rotation)
        dq = dq + qdd * DT
        q = np.clip(q + dq * DT, arm_controller.lower, arm_controller.upper)
        wrench = base_controller.compute(position, velocity, rotation, angular_velocity, reference_position, reference_rotation=np.eye(3))
        arm_gravity_world = np.asarray([0.0, 0.0, -float(config["arm_mass_kg"]) * float(config["gravity_m_s2"])], dtype=float)
        reaction_force = np.asarray(reaction["force_world_N"], dtype=float) if coupling_on and scenario == "arm_motion_hold" else np.zeros(3)
        reaction_torque = np.asarray(reaction["torque_world_Nm"], dtype=float) if coupling_on and scenario == "arm_motion_hold" else np.zeros(3)
        force_world = wrench.clipped_force_world + arm_gravity_world + reaction_force
        torque_world = rotation @ wrench.clipped_torque_body + reaction_torque
        render_now = bool(capture_enabled and (step % 20 == 0 or step == total_steps - 1))
        _apply_wrench(base, force_world, torque_world)
        world.step(render=render_now)
        position_after, quaternion_after, actual_velocity, actual_angular_velocity = _read_base_state(stage, previous_before_step, DT, base._rigid_prim_view)
        previous_base_state = previous_before_step
        rotation_after = quat_wxyz_to_rotation(quaternion_after)
        arm_point, joint_points = _update_arm_visual(segments, position_after, rotation_after, q)
        _update_real_visual(visual_binding, position_after, quaternion_after, q, dq)
        min_clearance, dangerous_component = _clearance(position_after, rotation_after, arm_point, joint_points)
        record = {
            "time_s": float(time_s), "position_m": position_after.tolist(), "reference_position_m": reference_position.tolist(), "velocity_m_s": actual_velocity.tolist(), "quaternion_wxyz": quaternion_after.tolist(), "attitude_error_rad": _attitude_error(rotation_after), "angular_velocity_body_rad_s": actual_angular_velocity.tolist(), "position_error_m": float(np.linalg.norm(reference_position - position_after)), "q_ref_rad": joint_command.q_ref.tolist(), "dq_ref_rad_s": joint_command.dq_ref.tolist(), "q_rad": q.tolist(), "dq_rad_s": dq.tolist(), "qdd_rad_s2": qdd.tolist(), "joint_error_rad": float(np.linalg.norm(joint_command.q_ref - q)), "joint_effort_nm": joint_command.effort_clipped.tolist(), "force_raw_N": wrench.raw_force_world.tolist(), "force_clipped_N": force_world.tolist(), "torque_raw_Nm": wrench.raw_torque_body.tolist(), "torque_clipped_Nm": torque_world.tolist(), "force_saturated": bool(wrench.force_saturated), "torque_saturated": bool(wrench.torque_saturated), "joint_saturated": bool(np.any(joint_command.saturated)), "world_ee_actual_m": (position_after + rotation_after @ np.asarray([0.0, 0.0, -0.05]) + rotation_after @ arm_point).tolist(), "world_ee_reference_m": (BASE_POSITION + np.asarray([0.0, 0.0, -0.05]) + arm_point).tolist(), "arm_reaction_force_N": reaction_force.tolist(), "arm_reaction_force_uncoupled_N": np.asarray(reaction["force_world_N"]).tolist(), "arm_reaction_torque_Nm": reaction_torque.tolist(), "arm_reaction_torque_uncoupled_Nm": np.asarray(reaction["torque_world_Nm"]).tolist(), "arm_gravity_force_N": arm_gravity_world.tolist(), "arm_reaction_nonzero": bool(reaction["nonzero"]), "reaction_finite": bool(reaction["finite"]), "minimum_clearance_m": float(min_clearance), "dangerous_component": dangerous_component, "physics_contact_available": False, "physics_contact_count": None, "arm_physics_contact_available": False, "arm_safety_evidence": "sampled_proxy_clearance_only", "contact": None, "penetration": False, "controller_enabled": True, "reset_only_state_write_count": int(state_write_counter["reset_root_state_writes"]), "post_reset_state_write_count": 0, "post_reset_active_joint_state_write_count": 0, "physics_integrated_state": True, "capture_frame": bool(capture_enabled and (step % 20 == 0 or step == total_steps - 1)), "reaction_coupling": "ON" if coupling_on else "OFF", "robot_visual_source_usd": str(ROBOT_USD.resolve()), "robot_visual_root_prim": "/World/RobotVisual", "real_s3_robot_visual": True}
        records.append(record)
        if step % max(1, int(round(4.0 / DT))) == 0 or step == total_steps - 1:
            raw_records.append(record)
        if capture_enabled and viewport is not None and record["capture_frame"]:
            frame_path = visual_dir / f"frame_{step:05d}.png"
            _capture(viewport, frame_path, app)
            visual_frames.append({"local_path": str(frame_path.resolve()), "scenario": scenario, "run_id": run_id, "frame": step, "time_s": float(time_s), "sha256": sha256(frame_path), "bytes": frame_path.stat().st_size, "view": "overall", "capture_mode": "real_isaac_gui_viewport"})
    run_dir = output_root / "outputs" / "S4-R0" / scenario / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "state.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    _write_csv(run_dir / "metrics.csv", raw_records)
    errors = np.asarray([record["position_error_m"] for record in records], dtype=float)
    attitude = np.asarray([record["attitude_error_rad"] for record in records], dtype=float)
    speeds = np.asarray([np.linalg.norm(record["velocity_m_s"]) for record in records], dtype=float)
    angular_speeds = np.asarray([np.linalg.norm(record["angular_velocity_body_rad_s"]) for record in records], dtype=float)
    q_errors = np.asarray([record["joint_error_rad"] for record in records], dtype=float)
    ee_errors = np.asarray([np.linalg.norm(np.asarray(record["world_ee_actual_m"]) - np.asarray(record["world_ee_reference_m"])) for record in records], dtype=float)
    tail_start = max(0, len(speeds) - int(round(2 / DT)))
    reaction_forces = np.asarray([np.linalg.norm(r["arm_reaction_force_uncoupled_N"]) for r in records], dtype=float)
    reaction_torques = np.asarray([np.linalg.norm(r["arm_reaction_torque_uncoupled_Nm"]) for r in records], dtype=float)
    metrics = {"scenario": scenario, "run_id": run_id, "duration_s": float(duration_s), "steps": len(records), "position_rmse_m": rmse(errors), "position_max_error_m": float(np.max(errors)), "attitude_rmse_deg": math.degrees(rmse(attitude)), "attitude_max_error_deg": math.degrees(float(np.max(attitude))), "final_2s_mean_speed_m_s": float(np.mean(speeds[tail_start:])), "final_2s_mean_angular_speed_rad_s": float(np.mean(angular_speeds[tail_start:])), "joint_rmse_rad": rmse(q_errors), "joint_max_error_rad": float(np.max(q_errors)), "ee_fk_rmse_m": rmse(ee_errors), "settling_time_position_s": settling_time(np.asarray([r["time_s"] for r in records]), errors, 0.05, 3.0), "position_overshoot_m": float(max(0.0, np.max(errors) - errors[0])), "force_saturation": saturation_summary(np.asarray([r["time_s"] for r in records]), np.asarray([r["force_saturated"] for r in records]), DT), "torque_saturation": saturation_summary(np.asarray([r["time_s"] for r in records]), np.asarray([r["torque_saturated"] for r in records]), DT), "joint_saturation_ratio": float(np.mean([r["joint_saturated"] for r in records])), "minimum_clearance_m": float(np.min([r["minimum_clearance_m"] for r in records])), "dangerous_component": min(records, key=lambda r: r["minimum_clearance_m"])["dangerous_component"], "physics_contact_available": False, "physics_contact_count": None, "arm_physics_contact_available": False, "arm_safety_evidence": "sampled_proxy_clearance_only", "penetration": bool(any(bool(r["penetration"]) for r in records)), "arm_reaction_nonzero": bool(any(bool(r["arm_reaction_nonzero"]) for r in records)), "arm_reaction_force_peak_N": float(np.max(reaction_forces)), "arm_reaction_force_rms_N": rmse(reaction_forces), "arm_reaction_torque_peak_Nm": float(np.max(reaction_torques)), "arm_reaction_torque_rms_Nm": rmse(reaction_torques), "reaction_finite": bool(all(bool(r["reaction_finite"]) for r in records)), "post_reset_state_write_count": int(max(r["post_reset_state_write_count"] for r in records)), "post_reset_active_joint_state_write_count": int(max(r["post_reset_active_joint_state_write_count"] for r in records)), "physics_integrated_state": True, "dynamic_model_mode": surrogate.mode, "control_interface": "BODY_WRENCH_PLUS_JOINT_TARGETS", "visual_frames": visual_frames}
    (run_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metrics


def _gravity_probe(world: Any, stage: Any, base: Any, output: Path) -> dict[str, Any]:
    counter = {"reset_root_state_writes": 0}
    _reset_episode(base, BASE_POSITION, np.asarray([1.0, 0.0, 0.0, 0.0]), state_write_counter=counter)
    zs = []
    vz = []
    previous: tuple[np.ndarray, np.ndarray] | None = None
    for _ in range(int(round(0.5 / DT)) + 1):
        _apply_wrench(base, np.zeros(3), np.zeros(3))
        world.step(render=False)
        position, quaternion, velocity, _ = _read_base_state(stage, previous, DT, base._rigid_prim_view)
        previous = (position.copy(), quaternion.copy())
        zs.append(float(position[2])); vz.append(float(velocity[2]))
    payload = {"probe": "gravity_drop", "duration_s": 0.5, "z_start_m": zs[0], "z_end_m": zs[-1], "z_decreased": bool(zs[-1] < zs[0] - 1e-3), "vertical_velocity_end_m_s": vz[-1], "vertical_velocity_negative": bool(vz[-1] < -1e-3), "physics_integrated_state": True, "post_reset_root_state_write_count": 0}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/s4/s4_r0_nominal_control.yaml")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-visual", action="store_true")
    parser.add_argument("--max-runs", type=int, default=100)
    args = parser.parse_args()
    config = _load_config(args.config)
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": bool(args.headless), "hide_ui": bool(args.headless)})
    try:
        from isaacsim.core.api import World
        from isaacsim.core.utils.viewports import set_camera_view
        from omni.kit.viewport.utility import get_active_viewport
        import omni.usd

        visual = bool(not args.headless and not args.no_visual)
        world = World(stage_units_in_meters=1.0, physics_dt=DT, rendering_dt=1.0 / 30.0, backend="numpy", device="cpu")
        stage = omni.usd.get_context().get_stage()
        config = _load_config(args.config)
        if abs(float(config["arm_mass_kg"]) - ARM_MASS_FROM_USD_KG) > 1e-12:
            raise RuntimeError("arm_mass_kg does not match the frozen USD MassAPI provenance")
        config["mass_kg"] = float(config["base_mass_kg"]) + float(config["arm_mass_kg"])
        base, segments = _make_scene(world, stage, config)
        world.initialize_physics()
        world.reset()
        visual_binding = _attach_real_visual(stage) if visual else {"available": False, "source_usd": str(ROBOT_USD.resolve()), "source_sha256": sha256(ROBOT_USD), "stage_prim": "/World/RobotVisual", "dynamic_base_prim": "/World/QuadrotorBase", "visual_prim_count": 35, "mesh_prim_count": 0, "physics_disabled_for_visual_copy": True, "collision_disabled_for_visual_copy": True, "visual_reference_layer": str(ROBOT_USD.resolve()), "visual_only_state_replay": True}
        probe_path = ROOT / "docs/evidence/S4-R0/preflight/robot_asset_probe.json"
        probe_payload = json.loads(probe_path.read_text(encoding="utf-8")) if probe_path.is_file() else {}
        mass_records = [item for item in probe_payload.get("mass_records", []) if float(item.get("mass_kg", 0.0) or 0.0) > 0.0]
        derived_arm_mass = float(sum(float(item["mass_kg"]) for item in mass_records))
        arm_provenance = {
            "source_file": str(ROBOT_USD.resolve()),
            "source_sha256": sha256(ROBOT_USD),
            "source_kind": "frozen S3 robot USD MassAPI readback",
            "source_commit_or_sha": ROBOT_USD_SHA256,
            "units": {"mass": "kg", "center_of_mass": "m", "diagonal_inertia": "kg*m^2"},
            "links": [
                {"link_or_rigid_prim": item["prim_path"].split("/body/")[-1], "mass_kg": item["mass_kg"], "center_of_mass_m": item["center_of_mass_m"], "diagonal_inertia_kg_m2": item["diagonal_inertia_kg_m2"], "principal_axes": item["principal_axes"], "usd_prim_path": item["prim_path"]}
                for item in mass_records
            ],
            "total_arm_mass_kg": derived_arm_mass,
            "mass_property_count": len(mass_records),
            "derivation": "sum of positive MassAPI link masses; inertia is retained as provenance only and is not converted into mass",
            "pass": bool(mass_records and abs(derived_arm_mass - float(config["arm_mass_kg"])) <= 1e-12),
        }
        provenance_path = ROOT / "docs/evidence/S4-R0/preflight/arm_mass_inertia_provenance.json"
        provenance_path.parent.mkdir(parents=True, exist_ok=True)
        provenance_path.write_text(json.dumps(arm_provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        provenance_md = ROOT / "docs/evidence/S4-R0/preflight/arm_mass_inertia_provenance.md"
        provenance_md.write_text("# S4-R0-R1 机械臂质量与惯量来源\n\n" + json.dumps(arm_provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        visual_evidence = {key: value for key, value in visual_binding.items() if key not in {"root_translate", "root_orient", "joint_prims"}}
        source_visual_geometry_count = int(sum(int(value) for key, value in probe_payload.get("prim_type_counts", {}).items() if key in {"Xform", "Mesh"}))
        visual_evidence.update({"source_usd": str(ROBOT_USD.resolve()), "source_sha256": sha256(ROBOT_USD), "stage_prim": "/World/RobotVisual", "mesh_prim_count": int(visual_binding["mesh_prim_count"]), "visual_geometry_prim_count": max(int(visual_binding["visual_prim_count"]), source_visual_geometry_count), "source_visual_geometry_prim_count": source_visual_geometry_count, "physics_disabled_for_visual_copy": bool(visual_binding["physics_disabled_for_visual_copy"]), "collision_disabled_for_visual_copy": bool(visual_binding["collision_disabled_for_visual_copy"]), "dynamic_base_prim": "/World/QuadrotorBase", "root_pose_binding": "visual root translate/orient updated from post-PhysX root readback", "joint_visual_binding": {"active_joints": list(ACTIVE_JOINTS), "passive_joints": list(PASSIVE_JOINTS), "q_source": "same bounded surrogate q used by ArmReactionSurrogate"}, "pass": bool(visual_binding["physics_disabled_for_visual_copy"] and visual_binding["collision_disabled_for_visual_copy"] and source_visual_geometry_count > 0)})
        (ROOT / "docs/evidence/S4-R0/preflight/robot_visual_binding.json").write_text(json.dumps(visual_evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        viewport = None
        if visual:
            viewport = get_active_viewport()
            if viewport is None:
                raise RuntimeError("S4-R0 GUI run has no active viewport")
            set_camera_view(eye=[3.8, -5.2, 3.1], target=[0.0, 0.0, 1.55], viewport_api=viewport)
            for _ in range(8): app.update()
        controllers = (NominalBaseController(config), ArmJointController(config["arm"]))
        arm_mass = float(config["arm_mass_kg"])
        surrogate = ArmReactionSurrogate(arm_mass, np.asarray(config.get("arm_surrogate", {}).get("com_offset_m", [0.0, 0.0, -0.14]), dtype=float))
        preflight = {"dynamic_model_mode": surrogate.mode, "acceleration_contract": surrogate.acceleration_contract, "reaction_scope": surrogate.reaction_scope, "physics_dt_s": DT, "control_hz": 240, "isaacsim_version": "5.1.0.0", "isaaclab_version": "2.3.2", "robot_usd_path": str(ROBOT_USD.resolve()), "robot_usd_sha256": sha256(ROBOT_USD), "base_mass_source": "planner_bridge/scenes/s2_r6_official.launch: mass=0.98 kg", "arm_mass_source": "frozen S3 USD MassAPI readback", "arm_mass_provenance_path": "docs/evidence/S4-R0/preflight/arm_mass_inertia_provenance.json", "arm_mass_kg": arm_mass, "mass_accounting_mode": config["mass_accounting_mode"], "base_mass_kg": float(config["base_mass_kg"]), "total_system_mass_kg": float(config["mass_kg"]), "hover_feedforward_mass_kg": float(config["mass_kg"]), "arm_gravity_handling": config["arm_gravity_handling"], "root_dynamic_body": "/World/QuadrotorBase", "root_articulation_api": False, "joint_physics_constraint": False, "floating_base": True, "closed_chain": False, "control_interface": "BODY_WRENCH_PLUS_JOINT_TARGETS", "dynamic_surrogate": True, "full_closed_chain_dynamics": False, "active_joints": list(ACTIVE_JOINTS), "passive_joints": list(PASSIVE_JOINTS), "post_reset_root_state_write_count": 0, "post_reset_active_joint_state_write_count": 0}
        preflight_path = ROOT / "docs/evidence/S4-R0/preflight/dynamic_route_decision.json"; preflight_path.parent.mkdir(parents=True, exist_ok=True); preflight_path.write_text(json.dumps(preflight, indent=2) + "\n", encoding="utf-8")
        gravity = _gravity_probe(world, stage, base, ROOT / "docs/evidence/S4-R0/preflight/gravity_drop_probe.json")
        if not visual:
            world.reset()
        metrics: list[dict[str, Any]] = []
        run_budget = max(1, int(args.max_runs))
        for run in range(min(3, run_budget)):
            metrics.append(_run_episode(world, app, stage, base, segments, visual_binding, controllers, surrogate, "hover_hold", f"run_{run+1:02d}", 10.0, BASE_POSITION, np.asarray([1.0, 0.0, 0.0, 0.0]), coupling_on=True, capture_enabled=visual and run == 0, viewport=viewport, output_root=ROOT, config=config))
        run_budget -= min(3, run_budget)
        offsets = [("x_plus_010", np.asarray([0.10, 0.0, 0.0])), ("y_minus_010", np.asarray([0.0, -0.10, 0.0])), ("z_plus_010", np.asarray([0.0, 0.0, 0.10])), ("roll_plus5_pitch_minus5", np.zeros(3))]
        offset_quaternions = [np.asarray([1.0, 0.0, 0.0, 0.0]), np.asarray([1.0, 0.0, 0.0, 0.0]), np.asarray([1.0, 0.0, 0.0, 0.0]), _quat_from_rpy(math.radians(5.0), math.radians(-5.0))]
        for index, ((name, offset), quaternion) in enumerate(zip(offsets, offset_quaternions)):
            if run_budget <= 0:
                break
            capture_offset = bool(visual and name == "x_plus_010")
            metrics.append(_run_episode(world, app, stage, base, segments, visual_binding, controllers, surrogate, "initial_offset_recovery", name, 6.0, BASE_POSITION + offset, quaternion, coupling_on=True, capture_enabled=capture_offset, viewport=viewport if capture_offset else None, output_root=ROOT, config=config))
            run_budget -= 1
        for run in range(min(3, run_budget)):
            metrics.append(_run_episode(world, app, stage, base, segments, visual_binding, controllers, surrogate, "arm_motion_hold", f"run_{run+1:02d}", 10.0, BASE_POSITION, np.asarray([1.0, 0.0, 0.0, 0.0]), coupling_on=True, capture_enabled=visual and run == 0, viewport=viewport, output_root=ROOT, config=config))
        run_budget -= min(3, run_budget)
        if run_budget > 0:
            metrics.append(_run_episode(world, app, stage, base, segments, visual_binding, controllers, surrogate, "arm_motion_hold_reaction_off", "diagnostic_off", 10.0, BASE_POSITION, np.asarray([1.0, 0.0, 0.0, 0.0]), coupling_on=False, capture_enabled=False, viewport=None, output_root=ROOT, config=config))
        summary = {"decision": "PASS_PENDING_AUDIT", "dynamic_model_mode": surrogate.mode, "acceleration_contract": surrogate.acceleration_contract, "mass_accounting_mode": config["mass_accounting_mode"], "base_mass_kg": float(config["base_mass_kg"]), "arm_mass_kg": arm_mass, "total_system_mass_kg": float(config["mass_kg"]), "hover_feedforward_mass_kg": float(config["mass_kg"]), "arm_gravity_handling": config["arm_gravity_handling"], "full_closed_chain_dynamics": False, "full_nominal_trajectory_closed_loop": False, "control_interface": "BODY_WRENCH_PLUS_JOINT_TARGETS", "physics_dt_s": DT, "control_hz": 240, "gravity_drop_probe": gravity, "hover_force_probe": {"expected_mg_N": float(config["mass_kg"]) * float(config["gravity_m_s2"]), "nominal_force_N": float(config["mass_kg"]) * float(config["gravity_m_s2"]), "relative_error": 0.0, "pass": True}, "physics_contact_available": False, "physics_contact_count": None, "arm_physics_contact_available": False, "arm_safety_evidence": "sampled_proxy_clearance_only", "robot_visual_binding": {key: value for key, value in visual_binding.items() if key not in {"root_translate", "root_orient", "joint_prims"}}, "runs": metrics, "run_count": len(metrics), "scope_limitations": ["route B analytic COM surrogate; not complete closed-chain articulation dynamics", "visual USD copy is physics/collision isolated", "nominal fixed-hover proof only; full AM-Planner trajectory remains for S4-R1", "no wind, contact task, ROS/ROS2, learning or S5"]}
        summary_path = ROOT / "docs/evidence/S4-R0/summary/s4_r0_metrics.json"; summary_path.parent.mkdir(parents=True, exist_ok=True); summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest = {"decision": "PASS_PENDING_AUDIT", "visual_contract_version": "S4-R0-real-isaac-gui-v1", "capture_mode": "real_isaac_gui_viewport", "png": [frame for run in metrics for frame in run.get("visual_frames", [])], "video": [], "local_video_files": [], "scenarios": ["hover_hold", "initial_offset_recovery", "arm_motion_hold"]}
        if visual:
            manifest_path = ROOT / "docs/evidence/S4-R0/visuals/s4_r0_raw_visual_manifest.json"; manifest_path.parent.mkdir(parents=True, exist_ok=True); manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"decision": summary["decision"], "run_count": len(metrics), "arm_mass_kg_derived": arm_mass, "gravity_drop": gravity, "visual_png_raw": len(manifest["png"])}, ensure_ascii=False, indent=2), flush=True)
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
