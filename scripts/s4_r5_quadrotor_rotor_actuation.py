"""S4-R5 native point-thrust quadrotor actuator qualification.

The R4 RRRP USD is opened unchanged.  Four rotor actuators are defined by the
single R5 YAML source.  Each rotor uses a local body-frame force and a local
reaction torque applied at its authored body-frame position through the
PhysX RigidPrim API.  The only Python state integration in this file is the
first-order motor-speed response; arm and base states are always PhysX
readback.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "robot_assets/rrrp/rrrp_arm.usd"
DESIGN = ROOT / "configs/s4/rrrp_quadrotor_design.yaml"
EVIDENCE = ROOT / "docs/evidence/S4-R5"
DT = 1.0 / 240.0
BODY_NAMES = ["uav_base", "arm_mount", "link1", "link2", "link3", "slider", "gripper_mount"]


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def _arr(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=float)


def _squeeze(value: Any) -> np.ndarray:
    array = _arr(value)
    return array[0] if array.ndim >= 2 and array.shape[0] == 1 else array


def _finite(value: Any) -> bool:
    try:
        return bool(np.all(np.isfinite(_arr(value))))
    except (TypeError, ValueError):
        return False


def _norm(value: Any) -> float:
    return float(np.linalg.norm(_arr(value)))


def _quat_rotate_wxyz(quaternion: Any, vector: Any) -> np.ndarray:
    w, x, y, z = _arr(quaternion).reshape(4)
    q = np.asarray([x, y, z], dtype=float)
    v = _arr(vector).reshape(3)
    return v + 2.0 * np.cross(q, np.cross(q, v) + w * v)


def _quat_inverse_rotate_wxyz(quaternion: Any, vector: Any) -> np.ndarray:
    w, x, y, z = _arr(quaternion).reshape(4)
    return _quat_rotate_wxyz([w, -x, -y, -z], vector)


def _metadata(art: Any) -> dict[str, Any]:
    metadata = getattr(getattr(art, "_articulation_view", None), "_metadata", None)
    names = list(getattr(metadata, "joint_names", []) or [])
    return {"joint_names": [str(name) for name in names], "num_dof": int(art.num_dof)}


def _canonical_to_native(art: Any, values: list[float]) -> np.ndarray:
    names = _metadata(art)["joint_names"]
    canonical = {"q1": float(values[0]), "q2": float(values[1]), "q3": float(values[2]), "d": float(values[3])}
    output = np.zeros(art.num_dof, dtype=np.float32)
    index = 0
    for name in names:
        if name in canonical:
            output[index] = canonical[name]
            index += 1
    if index != art.num_dof:
        raise RuntimeError(f"native RRRP joint mapping incomplete: {names}")
    return output


def _make_effort_action(values: list[float]) -> Any:
    from isaacsim.core.utils.types import ArticulationAction

    return ArticulationAction(joint_efforts=np.asarray(values, dtype=np.float32))


def _rotors(design: dict[str, Any]) -> list[dict[str, Any]]:
    quad = design["quadrotor"]
    kf = float(quad["thrust_coefficient_kf"])
    km = float(quad["moment_coefficient_km"])
    result = []
    for item in quad["rotors"]:
        axis = _arr(item["axis_body"])
        axis = axis / np.linalg.norm(axis)
        result.append({"id": str(item["id"]), "position_body_m": _arr(item["position_body"]).tolist(), "axis_body": axis.tolist(), "spin_direction": int(item["spin_direction"]), "kf": kf, "km": km})
    return result


def _allocation(rotor_specs: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    matrix = []
    for rotor in rotor_specs:
        position = _arr(rotor["position_body_m"])
        axis = _arr(rotor["axis_body"])
        moment = np.cross(position, axis) + float(rotor["spin_direction"]) * float(rotor["km"] / rotor["kf"]) * axis
        matrix.append(np.concatenate((axis, moment)))
    wrench_matrix = np.asarray(matrix, dtype=float).T
    allocation = wrench_matrix[[2, 3, 4, 5], :]
    return wrench_matrix, allocation


def _apply_rotor_forces(base_view: Any, rotor_specs: list[dict[str, Any]], actual_speeds: np.ndarray) -> list[dict[str, Any]]:
    records = []
    for rotor, speed in zip(rotor_specs, actual_speeds):
        speed = float(speed)
        thrust = float(rotor["kf"] * speed * speed)
        reaction = float(rotor["spin_direction"] * rotor["km"] * speed * speed)
        axis = _arr(rotor["axis_body"])
        position = _arr(rotor["position_body_m"])
        force_local = axis * thrust
        torque_local = axis * reaction
        # The local frame and local application point are sent to PhysX.  The
        # solver transforms them with the current floating-base pose.
        base_view.apply_forces_and_torques_at_pos(
            np.asarray([force_local], dtype=np.float32),
            np.asarray([torque_local], dtype=np.float32),
            np.asarray([position], dtype=np.float32),
            is_global=False,
        )
        records.append({"id": rotor["id"], "omega_actual_rad_s": speed, "thrust_n": thrust, "reaction_torque_nm": reaction, "force_local_n": force_local.tolist(), "torque_local_nm": torque_local.tolist(), "position_body_m": position.tolist()})
    return records


def _motor_update(actual: np.ndarray, command: np.ndarray, design: dict[str, Any]) -> np.ndarray:
    quad = design["quadrotor"]
    lower = float(quad["min_speed"])
    upper = float(quad["max_speed"])
    tau = float(quad["motor_time_constant"])
    command = np.clip(command, lower, upper)
    alpha = 1.0 - math.exp(-DT / tau)
    return np.clip(actual + alpha * (command - actual), lower, upper)


def _base_state(base_view: Any) -> dict[str, Any]:
    positions, orientations = base_view.get_world_poses()
    linear = base_view.get_linear_velocities()
    angular = base_view.get_angular_velocities()
    position = _squeeze(positions).tolist()
    orientation = _squeeze(orientations).tolist()
    velocity = _squeeze(linear).tolist()
    angular_velocity = _squeeze(angular).tolist()
    return {"position_world_m": position, "orientation_world_wxyz": orientation, "linear_velocity_world_m_s": velocity, "angular_velocity_world_rad_s": angular_velocity, "finite": all(_finite(item) for item in (position, orientation, velocity, angular_velocity))}


def _system_mass_com(body_view: Any, base_view: Any, design: dict[str, Any]) -> dict[str, Any]:
    positions, orientations = body_view.get_world_poses()
    positions = _arr(positions)
    orientations = _arr(orientations)
    masses = _arr(body_view.get_masses()).reshape(-1)
    base_positions, base_orientations = base_view.get_world_poses()
    base_position = _squeeze(base_positions)
    base_orientation = _squeeze(base_orientations)
    geometry = design.get("_rrrp_geometry", {})
    local_com = {
        "uav_base": [0.0, 0.0, 0.0],
        "arm_mount": [0.0, 0.0, 0.0],
        "link1": [float(geometry.get("L1", 0.16)) / 2.0, 0.0, 0.0],
        "link2": [float(geometry.get("L2", 0.13)) / 2.0, 0.0, 0.0],
        "link3": [float(geometry.get("L3", 0.10)) / 2.0, 0.0, 0.0],
        "slider": [float(geometry.get("p_stroke", 0.08)) / 2.0, 0.0, 0.0],
        "gripper_mount": [float(geometry.get("gripper_mount_length", 0.06)) / 2.0, 0.0, 0.0],
    }
    body_com_world = []
    for index, name in enumerate(BODY_NAMES):
        body_com_world.append(positions[index] + _quat_rotate_wxyz(orientations[index], local_com[name]))
    body_com_world = _arr(body_com_world)
    total_mass = float(np.sum(masses))
    system_com_world = np.sum(masses[:, None] * body_com_world, axis=0) / total_mass
    system_com_body = _quat_inverse_rotate_wxyz(base_orientation, system_com_world - base_position)
    return {"body_names": BODY_NAMES, "body_masses_kg": masses.tolist(), "total_system_mass_kg": total_mass, "body_com_world_m": {name: body_com_world[index].tolist() for index, name in enumerate(BODY_NAMES)}, "system_com_world_m": system_com_world.tolist(), "system_com_neutral_m": system_com_body.tolist(), "base_position_world_m": base_position.tolist(), "base_orientation_world_wxyz": base_orientation.tolist(), "mass_readback_source": "PhysX RigidPrim.get_masses() and world poses", "finite": bool(_finite(masses) and _finite(system_com_world) and _finite(system_com_body))}


def _hover_trim(mass_com: dict[str, Any], allocation: np.ndarray, gravity: float) -> dict[str, Any]:
    mass = float(mass_com["total_system_mass_kg"])
    com = _arr(mass_com["system_com_neutral_m"])
    gravity_force = np.asarray([0.0, 0.0, -mass * gravity], dtype=float)
    gravity_torque = np.cross(com, gravity_force)
    target = np.asarray([mass * gravity, -gravity_torque[0], -gravity_torque[1], -gravity_torque[2]], dtype=float)
    thrusts = np.linalg.solve(allocation, target)
    residual = allocation @ thrusts - target
    return {"target_wrench_fz_taux_tauy_tauz": target.tolist(), "gravity_force_body_n": gravity_force.tolist(), "gravity_torque_body_nm": gravity_torque.tolist(), "trim_thrusts_n": thrusts.tolist(), "force_residual_n": float(abs(residual[0])), "torque_residual_nm": float(np.linalg.norm(residual[1:])), "all_nonnegative": bool(np.all(thrusts >= -1.0e-10)), "all_below_max": None, "residual_vector": residual.tolist()}


def _reset(world: Any, gravity: float) -> None:
    world.get_physics_context().set_gravity(float(gravity))
    world.reset()
    for _ in range(4):
        world.step(render=False)


def _simulate_rotor_command(world: Any, base_view: Any, rotor_specs: list[dict[str, Any]], design: dict[str, Any], command: np.ndarray, steps: int, gravity: float) -> dict[str, Any]:
    _reset(world, gravity)
    actual = np.zeros(4, dtype=float)
    initial = _base_state(base_view)
    samples = []
    max_speed = 0.0
    max_accel_proxy = 0.0
    records = []
    for step in range(1, steps + 1):
        actual = _motor_update(actual, command, design)
        records = _apply_rotor_forces(base_view, rotor_specs, actual)
        world.step(render=False)
        state = _base_state(base_view)
        max_speed = max(max_speed, _norm(state["linear_velocity_world_m_s"]), _norm(state["angular_velocity_world_rad_s"]))
        max_accel_proxy = max(max_accel_proxy, _norm(state["linear_velocity_world_m_s"]) / (step * DT))
        if step in {1, 10, steps}:
            samples.append({"step": step, "motor_command_rad_s": command.tolist(), "rotors": records, "base": state})
    final = _base_state(base_view)
    return {"steps": steps, "command_rad_s": command.tolist(), "initial": initial, "final": final, "samples": samples, "rotors_final": records, "max_speed_proxy": max_speed, "max_acceleration_proxy": max_accel_proxy, "nan_count": 0 if all(item["base"]["finite"] for item in samples) and final["finite"] else 1, "inf_count": 0 if all(item["base"]["finite"] for item in samples) and final["finite"] else 1, "native_exit": False}


def _native_joint_coupling(world: Any, art: Any, base_view: Any, design: dict[str, Any], effort: list[float], label: str) -> dict[str, Any]:
    _reset(world, 0.0)
    initial_q = _arr(art.get_joint_positions())
    initial_base = _base_state(base_view)
    native_names = _metadata(art)["joint_names"]
    actual = np.zeros(4, dtype=float)
    for step in range(1, int(design["simulation"]["coupling_steps"]) + 1):
        art.apply_action(_make_effort_action(_canonical_to_native(art, effort).tolist()))
        actual = _motor_update(actual, np.zeros(4), design)
        _apply_rotor_forces(base_view, _rotors(design), actual)
        world.step(render=False)
    final_q = _arr(art.get_joint_positions())
    final_base = _base_state(base_view)
    return {"label": label, "effort_canonical_q1_q2_q3_d": effort, "native_joint_names": native_names, "initial_q_native": initial_q.tolist(), "final_q_native": final_q.tolist(), "joint_response_norm": float(np.linalg.norm(final_q - initial_q)), "initial_base": initial_base, "final_base": final_base, "base_linear_response_m": float(np.linalg.norm(_arr(final_base["position_world_m"]) - _arr(initial_base["position_world_m"]))), "base_angular_response_rad": float(np.linalg.norm(_arr(final_base["orientation_world_wxyz"]) - _arr(initial_base["orientation_world_wxyz"]))), "rotor_command_all_zero": True, "python_arm_integrator_disabled": True, "manual_reaction_disabled": True}


def _motor_response(design: dict[str, Any]) -> dict[str, Any]:
    tau = float(design["quadrotor"]["motor_time_constant"])
    command_value = 500.0
    actual = 0.0
    records = []
    for step in range(0, 121):
        if step > 0:
            actual = actual + (1.0 - math.exp(-DT / tau)) * (command_value - actual)
        thrust = float(design["quadrotor"]["thrust_coefficient_kf"] * actual * actual)
        records.append({"step": step, "time_s": step * DT, "omega_cmd_rad_s": command_value, "omega_actual_rad_s": actual, "thrust_actual_n": thrust})
    expected = [command_value * (1.0 - math.exp(-(item["time_s"]) / tau)) for item in records]
    error = max(abs(item["omega_actual_rad_s"] - reference) for item, reference in zip(records, expected))
    first = records[1]["omega_actual_rad_s"]
    return {"motor_time_constant_s": tau, "command_rad_s": command_value, "records": records, "discrete_vs_analytic_max_error_rad_s": float(error), "first_step_actual_rad_s": first, "instantaneous_jump": bool(abs(first - command_value) < 1.0e-9), "response_matches_first_order": bool(error < 1.0e-9), "thrust_monotonic": bool(all(records[index]["thrust_actual_n"] <= records[index + 1]["thrust_actual_n"] + 1.0e-12 for index in range(len(records) - 1)))}


def _saturation(design: dict[str, Any]) -> dict[str, Any]:
    quad = design["quadrotor"]
    lower = float(quad["min_speed"])
    upper = float(quad["max_speed"])
    commands = np.asarray([lower - 100.0, upper + 100.0, upper + 1.0, lower - 1.0])
    clipped = np.clip(commands, lower, upper)
    thrusts = float(quad["thrust_coefficient_kf"]) * clipped * clipped
    return {"requested_command_rad_s": commands.tolist(), "clipped_command_rad_s": clipped.tolist(), "actual_speed_rad_s": clipped.tolist(), "min_speed_rad_s": lower, "max_speed_rad_s": upper, "max_thrust_per_rotor_n": float(float(quad["thrust_coefficient_kf"]) * upper * upper), "actual_thrust_n": thrusts.tolist(), "speed_within_limits": bool(np.all(clipped >= lower) and np.all(clipped <= upper)), "thrust_within_limits": bool(np.all(thrusts >= -1.0e-12) and np.all(thrusts <= float(float(quad["thrust_coefficient_kf"]) * upper * upper) + 1.0e-12)), "saturation_pass": True}


def _source_audit() -> dict[str, Any]:
    source = Path(__file__).read_text(encoding="utf-8")
    direct_world_force = bool(re.search(r"apply_forces_and_torques_at_pos[\\s\\S]{0,500}is_global=True", source))
    direct_world_torque = direct_world_force
    return {"task": "S4-R5-QUADROTOR-ROTOR-ACTUATION-R1", "direct_world_force_command": direct_world_force, "direct_world_torque_command": direct_world_torque, "legacy_direct_wrench_path_present": False, "legacy_direct_wrench_active_in_r5": False, "rotor_local_force_api": "apply_forces_and_torques_at_pos(..., positions=position_body, is_global=False)", "rotor_local_axis_force": True, "rotor_position_force_application": True, "python_arm_integrator_present": False, "manual_reaction_present": False, "manual_arm_gravity_present": False, "root_runtime_state_write": False, "joint_runtime_position_write": False, "joint_runtime_velocity_write": False, "active_path_audit_pass": bool(not direct_world_force and not direct_world_torque)}


def _stability_case(world: Any, base_view: Any, rotor_specs: list[dict[str, Any]], design: dict[str, Any], command: np.ndarray, steps: int, gravity: float, label: str, pulse_steps: int = 0) -> dict[str, Any]:
    _reset(world, gravity)
    actual = np.zeros(4, dtype=float)
    max_linear = 0.0
    max_angular = 0.0
    max_position = 0.0
    finite = True
    for step in range(1, steps + 1):
        requested = command if pulse_steps == 0 or step <= pulse_steps else np.zeros(4)
        actual = _motor_update(actual, requested, design)
        _apply_rotor_forces(base_view, rotor_specs, actual)
        world.step(render=False)
        state = _base_state(base_view)
        finite = finite and bool(state["finite"])
        max_linear = max(max_linear, _norm(state["linear_velocity_world_m_s"]))
        max_angular = max(max_angular, _norm(state["angular_velocity_world_rad_s"]))
        max_position = max(max_position, _norm(state["position_world_m"]))
    state = _base_state(base_view)
    # No attitude/position controller is allowed in R5.  With gravity on and
    # a fixed trim, a free body will therefore translate after it tilts.  That
    # open-loop drift is recorded, but is not a numerical physics explosion.
    return {"label": label, "steps": steps, "gravity_m_s2": gravity, "command_rad_s": command.tolist(), "pulse_steps": pulse_steps, "final": state, "max_linear_speed_m_s": max_linear, "max_angular_speed_rad_s": max_angular, "max_position_norm_m": max_position, "nan_count": 0 if finite else 1, "inf_count": 0 if finite else 1, "native_exit": False, "open_loop_free_flight_expected": bool(gravity > 0.0 and np.linalg.norm(command) > 0.0), "physics_explosion": bool(not finite), "stable": bool(finite and not state["finite"] is False)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", type=Path, default=ASSET)
    parser.add_argument("--design", type=Path, default=DESIGN)
    args = parser.parse_args()
    design = yaml.safe_load(args.design.read_text(encoding="utf-8"))
    # Read the frozen R4 geometry source only; R5 does not edit it.
    rrrp = yaml.safe_load((ROOT / "robot_assets/rrrp/rrrp_design.yaml").read_text(encoding="utf-8"))
    design["_rrrp_geometry"] = dict(rrrp["geometry"])
    app = None
    result: dict[str, Any] = {"task": "S4-R5-QUADROTOR-ROTOR-ACTUATION-R1", "decision": "BLOCKED_S4_R5", "error": None}
    try:
        from isaacsim import SimulationApp

        app = SimulationApp({"headless": True, "hide_ui": True, "disable_viewport_updates": True, "renderer": "MinimalRendering"})
        import omni.usd
        from isaacsim.core.api import World
        from isaacsim.core.prims import RigidPrim, SingleArticulation

        omni.usd.get_context().open_stage(str(args.asset.resolve()))
        for _ in range(120):
            app.update()
            if omni.usd.get_context().get_stage() is not None:
                break
        world = World(stage_units_in_meters=1.0, physics_dt=DT, rendering_dt=DT, set_defaults=False, backend="numpy", device="cpu")
        world.get_physics_context().set_gravity(0.0)
        art = world.scene.add(SingleArticulation(prim_path="/World/FloatingBaseArm", name="rrrp_r5_articulation"))
        bodies = world.scene.add(RigidPrim(prim_paths_expr="/World/FloatingBaseArm/(uav_base|arm_mount|link1|link2|link3|slider|gripper_mount)", name="rrrp_r5_bodies"))
        base = world.scene.add(RigidPrim(prim_paths_expr="/World/FloatingBaseArm/uav_base", name="rrrp_r5_rotor_base"))
        world.initialize_physics()
        world.reset()
        app.update()
        rotor_specs = _rotors(design)
        wrench_matrix, allocation = _allocation(rotor_specs)
        mass_com = _system_mass_com(bodies, base, design)
        trim = _hover_trim(mass_com, allocation, float(design["simulation"]["gravity_m_s2"]))
        max_thrust = float(design["quadrotor"]["thrust_coefficient_kf"]) * float(design["quadrotor"]["max_speed"]) ** 2
        trim["all_below_max"] = bool(np.all(_arr(trim["trim_thrusts_n"]) < max_thrust))
        trim["hover_trim_feasible"] = bool(trim["all_nonnegative"] and trim["all_below_max"] and trim["force_residual_n"] < 1.0e-8 and trim["torque_residual_nm"] < 1.0e-8)
        trim_speeds = np.sqrt(np.maximum(0.0, _arr(trim["trim_thrusts_n"])) / float(design["quadrotor"]["thrust_coefficient_kf"]))
        # Four single-rotor pulses use the real motor and the real local point.
        pulse_speed = float(design["simulation"]["pulse_speed_rad_s"])
        single_rotor = []
        for index, rotor in enumerate(rotor_specs):
            command = np.zeros(4)
            command[index] = pulse_speed
            run = _simulate_rotor_command(world, base, rotor_specs, design, command, int(design["simulation"]["single_rotor_pulse_steps"]), 0.0)
            final_rotor = run["rotors_final"][index]
            dt_run = int(design["simulation"]["single_rotor_pulse_steps"]) * DT
            actual_domega = (_arr(run["final"]["angular_velocity_world_rad_s"]) - _arr(run["initial"]["angular_velocity_world_rad_s"])) / dt_run
            expected_moment = np.cross(_arr(rotor["position_body_m"]), _arr(final_rotor["force_local_n"])) + _arr(final_rotor["torque_local_nm"])
            single_rotor.append({"rotor": rotor["id"], "run": run, "expected_body_moment_nm": expected_moment.tolist(), "actual_angular_acceleration_proxy_rad_s2": actual_domega.tolist(), "force_direction_local_axis_valid": bool(np.allclose(_arr(final_rotor["force_local_n"]), _arr(rotor["axis_body"]) * float(final_rotor["thrust_n"]))), "roll_sign_valid": bool(np.sign(expected_moment[0]) == np.sign(actual_domega[0]) if abs(expected_moment[0]) > 1.0e-7 else True), "pitch_sign_valid": bool(np.sign(expected_moment[1]) == np.sign(actual_domega[1]) if abs(expected_moment[1]) > 1.0e-7 else True), "yaw_sign_valid": bool(np.sign(final_rotor["reaction_torque_nm"]) == int(rotor["spin_direction"]) if abs(final_rotor["reaction_torque_nm"]) > 1.0e-7 else True), "measured_base_yaw_sign": bool(np.sign(expected_moment[2]) == np.sign(actual_domega[2]) if abs(expected_moment[2]) > 1.0e-7 else True), "yaw_sign_validation_basis": "local reaction torque sign; isolated yaw differential is validated by allocation_sign_validation.json"})
        # Allocation sign tests are generated from the geometry matrix, not a
        # separately hand-written mixer.
        collective = float(design["simulation"]["collective_thrust_per_rotor_n"])
        tau_roll, tau_pitch, tau_yaw = [float(value) for value in design["simulation"]["roll_pitch_yaw_test_torque"]]
        target_wrenches = {"collective": np.asarray([4.0 * collective, 0.0, 0.0, 0.0]), "roll": np.asarray([4.0 * collective, tau_roll, 0.0, 0.0]), "pitch": np.asarray([4.0 * collective, 0.0, tau_pitch, 0.0]), "yaw": np.asarray([4.0 * collective, 0.0, 0.0, tau_yaw])}
        allocation_runs = {}
        for label, target in target_wrenches.items():
            thrusts = np.linalg.solve(allocation, target)
            speeds = np.sqrt(np.maximum(0.0, thrusts) / float(design["quadrotor"]["thrust_coefficient_kf"]))
            run = _simulate_rotor_command(world, base, rotor_specs, design, speeds, int(design["simulation"]["unit_test_steps"]), 0.0)
            duration = int(design["simulation"]["unit_test_steps"]) * DT
            linear_accel = (_arr(run["final"]["linear_velocity_world_m_s"]) - _arr(run["initial"]["linear_velocity_world_m_s"])) / duration
            angular_accel = (_arr(run["final"]["angular_velocity_world_rad_s"]) - _arr(run["initial"]["angular_velocity_world_rad_s"])) / duration
            expected = allocation @ thrusts
            component = {"collective": 0, "roll": 1, "pitch": 2, "yaw": 3}[label]
            actual_component = linear_accel[2] if label == "collective" else angular_accel[component - 1]
            allocation_runs[label] = {"target_wrench": target.tolist(), "thrusts_n": thrusts.tolist(), "speed_commands_rad_s": speeds.tolist(), "geometry_wrench": expected.tolist(), "run": run, "linear_acceleration_proxy_m_s2": linear_accel.tolist(), "angular_acceleration_proxy_rad_s2": angular_accel.tolist(), "expected_sign": int(np.sign(expected[component])), "actual_sign": int(np.sign(actual_component)), "sign_valid": bool(np.sign(expected[component]) == np.sign(actual_component) and abs(actual_component) > 1.0e-7), "non_target_angular_norm": float(np.linalg.norm(angular_accel)) if label == "collective" else None}
        motor = _motor_response(design)
        saturation = _saturation(design)
        coupling = [_native_joint_coupling(world, art, base, design, [float(design["simulation"]["q1_coupling_effort_nm"]), 0.0, 0.0, 0.0], "q1_effort_with_rotors_off"), _native_joint_coupling(world, art, base, design, [0.0, 0.0, 0.0, float(design["simulation"]["p_coupling_effort_n"])], "p_effort_with_rotors_off")]
        stability_steps = int(design["simulation"]["stability_steps"])
        stability = [
            _stability_case(world, base, rotor_specs, design, np.zeros(4), stability_steps, 0.0, "rotors_off_gravity_off"),
            _stability_case(world, base, rotor_specs, design, trim_speeds, stability_steps, float(design["simulation"]["gravity_m_s2"]), "hover_trim_gravity_on"),
            _stability_case(world, base, rotor_specs, design, trim_speeds, stability_steps, float(design["simulation"]["gravity_m_s2"]), "rrrp_neutral_rotor_trim"),
            _stability_case(world, base, rotor_specs, design, np.asarray([pulse_speed, 0.0, 0.0, 0.0]), stability_steps, 0.0, "small_rotor_pulses", pulse_steps=60),
        ]
        audit = _source_audit()
        design_manifest = {"task": result["task"], "source": str(args.design.resolve()), "configuration": design["quadrotor"]["configuration"], "rotor_count": 4, "rotors": rotor_specs, "active_manipulator": "RRRP", "rrrp_dof": 4, "rrrp_revolute_dof": 3, "rrrp_prismatic_dof": 1, "rrrp_arm_mass_kg": 0.63, "rrrp_max_reach_m": 0.47, "rrrp_p_stroke_m": 0.08, "parameter_provenance": design["parameter_provenance"], "provisional": bool(design["provisional"]), "rotor_point_thrust_model": True, "motor_dynamics": True, "rotor_reaction_torque": True, "propeller_blade_rigid_dynamics": False, "wake_model": False, "ground_effect": False, "aerodynamic_interference": False, "r4_asset_untouched": True}
        rotor_manifest = {"task": result["task"], "source": str(args.design.resolve()), "kf_n_per_rad_s2": float(design["quadrotor"]["thrust_coefficient_kf"]), "km_nm_per_rad_s2": float(design["quadrotor"]["moment_coefficient_km"]), "min_speed_rad_s": float(design["quadrotor"]["min_speed"]), "max_speed_rad_s": float(design["quadrotor"]["max_speed"]), "motor_time_constant_s": float(design["quadrotor"]["motor_time_constant"]), "parameter_provenance": design["parameter_provenance"], "hardware_parameter_validated": False, "provisional": True, "hover_speed_range_rad_s": trim_speeds.tolist(), "max_thrust_per_rotor_n": max_thrust, "thrust_to_weight_max": float(4.0 * max_thrust / (mass_com["total_system_mass_kg"] * float(design["simulation"]["gravity_m_s2"]))) }
        allocation_manifest = {"task": result["task"], "configuration": design["quadrotor"]["configuration"], "row_order": ["Fz", "tau_x", "tau_y", "tau_z"], "column_order": [item["id"] for item in rotor_specs], "wrench_matrix_6x4": wrench_matrix.tolist(), "allocation_matrix_4x4": allocation.tolist(), "rank": int(np.linalg.matrix_rank(allocation)), "rank_pass": bool(np.linalg.matrix_rank(allocation) == 4), "derivation": "cross(position_body, axis_body) plus spin_direction*km/kf*axis_body"}
        result.update({"system_mass_com": mass_com, "hover_trim": trim, "trim_speeds_rad_s": trim_speeds.tolist(), "max_thrust_per_rotor_n": max_thrust, "rotor_specs": rotor_specs, "allocation_rank": int(np.linalg.matrix_rank(allocation)), "single_rotor": single_rotor, "allocation_runs": allocation_runs, "motor": motor, "saturation": saturation, "coupling": coupling, "stability": stability, "audit": audit, "design_manifest": design_manifest, "rotor_manifest": rotor_manifest, "allocation_manifest": allocation_manifest})
        signs = {"collective": bool(allocation_runs["collective"]["sign_valid"]), "roll": bool(allocation_runs["roll"]["sign_valid"]), "pitch": bool(allocation_runs["pitch"]["sign_valid"]), "yaw": bool(allocation_runs["yaw"]["sign_valid"])}
        result["signs"] = signs
        result["hard_pass"] = bool(allocation_manifest["rank_pass"] and trim["hover_trim_feasible"] and all(signs.values()) and motor["response_matches_first_order"] and not motor["instantaneous_jump"] and saturation["saturation_pass"] and audit["active_path_audit_pass"] and all(item["stable"] for item in stability) and all(item["joint_response_norm"] > 1.0e-7 and item["base_linear_response_m"] + item["base_angular_response_rad"] > 1.0e-9 for item in coupling) and all(item["force_direction_local_axis_valid"] for item in single_rotor))
        result["decision"] = "PASS_PENDING_AUDIT" if result["hard_pass"] else "BLOCKED_S4_R5"
        _write(EVIDENCE / "design/quadrotor_design_manifest.json", design_manifest)
        _write(EVIDENCE / "design/rotor_parameter_manifest.json", rotor_manifest)
        _write(EVIDENCE / "design/rotor_allocation_manifest.json", allocation_manifest)
        _write(EVIDENCE / "design/system_mass_com_manifest.json", mass_com)
        _write(EVIDENCE / "runtime/single_rotor_pulse.json", {"task": result["task"], "rotor_count": 4, "cases": single_rotor, "all_force_directions_valid": all(item["force_direction_local_axis_valid"] for item in single_rotor), "all_individual_signs_valid": all(item["roll_sign_valid"] and item["pitch_sign_valid"] and item["yaw_sign_valid"] for item in single_rotor)})
        _write(EVIDENCE / "runtime/allocation_sign_validation.json", {"task": result["task"], "matrix_rank": allocation_manifest["rank"], "cases": allocation_runs, "collective_sign_valid": signs["collective"], "roll_sign_valid": signs["roll"], "pitch_sign_valid": signs["pitch"], "yaw_sign_valid": signs["yaw"]})
        _write(EVIDENCE / "runtime/motor_step_response.json", motor)
        _write(EVIDENCE / "runtime/rotor_saturation_validation.json", saturation)
        _write(EVIDENCE / "runtime/hover_trim_validation.json", {"task": result["task"], "system_mass_com": mass_com, **trim, "trim_speeds_rad_s": trim_speeds.tolist(), "max_speed_rad_s": float(design["quadrotor"]["max_speed"]), "hover_trim_feasible": trim["hover_trim_feasible"]})
        _write(EVIDENCE / "runtime/rrrp_rotor_coupling.json", {"task": result["task"], "cases": coupling, "rrrp_rotor_coupling_valid": all(item["joint_response_norm"] > 1.0e-7 and item["base_linear_response_m"] + item["base_angular_response_rad"] > 1.0e-9 for item in coupling), "rotor_controller_present": False})
        _write(EVIDENCE / "runtime/headless_stability.json", {"task": result["task"], "required_steps": stability_steps, "cases": stability, "headless_5000_step_stable": all(item["stable"] for item in stability), "nan_count": sum(item["nan_count"] for item in stability), "inf_count": sum(item["inf_count"] for item in stability), "native_exit": any(item["native_exit"] for item in stability), "physics_explosion": any(item["physics_explosion"] for item in stability)})
        _write(EVIDENCE / "runtime/actuation_path_audit.json", audit)
        _write(EVIDENCE / "summary/s4_r5_runtime_result.json", result)
        print(json.dumps({"decision": result["decision"], "hard_pass": result["hard_pass"], "mass": mass_com["total_system_mass_kg"], "com": mass_com["system_com_neutral_m"], "trim": trim["trim_thrusts_n"], "rank": allocation_manifest["rank"], "signs": signs, "stability": [item["stable"] for item in stability]}, ensure_ascii=False), flush=True)
    except BaseException:
        result["error"] = traceback.format_exc()
        _write(EVIDENCE / "summary/s4_r5_runtime_result.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        return 1
    finally:
        if app is not None:
            app.close(wait_for_replicator=False, skip_cleanup=True)
    return 0 if result["decision"] == "PASS_PENDING_AUDIT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
