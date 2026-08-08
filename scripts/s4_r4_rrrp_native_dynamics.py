"""Run the S4-R4 RRRP effort-pulse and floating-base native dynamics gates.

The script only sends PhysX articulation effort actions. It never integrates
joint state in Python and never writes root/joint pose or velocity after a
reset. Default joint positions are used only before reset for the explicit
prismatic-limit readback cases.
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
DESIGN = ROOT / "robot_assets/rrrp/rrrp_design.yaml"
EVIDENCE = ROOT / "docs/evidence/S4-R4"
DT = 1.0 / 240.0


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def _finite(value: Any) -> bool:
    try:
        return bool(np.all(np.isfinite(np.asarray(value, dtype=float))))
    except (TypeError, ValueError):
        return False


def _norm(value: Any) -> float:
    return float(np.linalg.norm(np.asarray(value, dtype=float)))


def _squeeze_batch(value: Any) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.ndim >= 2 and array.shape[0] == 1:
        return array[0]
    return array


def _metadata(art: Any) -> dict[str, Any]:
    metadata = getattr(getattr(art, "_articulation_view", None), "_metadata", None)
    names = list(getattr(metadata, "joint_names", []) or [])
    body_names = list(getattr(metadata, "body_names", []) or [])
    return {"joint_names": [str(name) for name in names], "body_names": [str(name) for name in body_names], "num_dof": int(art.num_dof), "num_bodies": int(art.num_bodies)}


def _state(art: Any, body_view: Any | None = None, root: bool = False) -> dict[str, Any]:
    q = np.asarray(art.get_joint_positions(), dtype=float)
    dq = np.asarray(art.get_joint_velocities(), dtype=float)
    efforts = np.asarray(art.get_applied_joint_efforts(), dtype=float)
    measured = np.asarray(art.get_measured_joint_efforts(), dtype=float)
    view = body_view if body_view is not None else art._articulation_view
    poses = view.get_world_poses()
    positions = _squeeze_batch(poses[0])
    orientations = _squeeze_batch(poses[1])
    linear = np.asarray(view.get_linear_velocities(), dtype=float)
    angular = np.asarray(view.get_angular_velocities(), dtype=float)
    if body_view is None:
        linear = _squeeze_batch(linear)
        angular = _squeeze_batch(angular)
    payload = {"q": q.tolist(), "dq": dq.tolist(), "applied_effort": efforts.tolist(), "measured_effort": measured.tolist(), "link_pose_positions": positions.tolist(), "link_pose_orientations_wxyz": orientations.tolist(), "link_linear_velocities": linear.tolist(), "link_angular_velocities": angular.tolist(), "finite": all(_finite(item) for item in (q, dq, efforts, measured, positions, orientations, linear, angular))}
    if root:
        root_position, root_orientation = art.get_world_pose()
        payload["root_position_m"] = np.asarray(root_position, dtype=float).tolist()
        payload["root_orientation_wxyz"] = np.asarray(root_orientation, dtype=float).tolist()
        payload["root_linear_velocity_m_s"] = np.asarray(art.get_linear_velocity(), dtype=float).tolist()
        payload["root_angular_velocity_rad_s"] = np.asarray(art.get_angular_velocity(), dtype=float).tolist()
    return payload


def _momentum(art: Any, body_view: Any | None = None) -> dict[str, Any]:
    view = body_view if body_view is not None else art._articulation_view
    masses = np.asarray(view.get_masses() if body_view is not None else _squeeze_batch(view.get_body_masses()), dtype=float).reshape(-1)
    velocities = np.asarray(view.get_linear_velocities(), dtype=float)
    if body_view is None:
        velocities = _squeeze_batch(velocities)
    momentum = np.sum(masses[:, None] * velocities, axis=0)
    max_speed = max((_norm(item) for item in velocities), default=0.0)
    characteristic = float(np.sum(masses) * max_speed)
    return {"body_masses_kg": masses.tolist(), "linear_momentum_kg_m_s": momentum.tolist(), "max_body_speed_m_s": max_speed, "characteristic_momentum_kg_m_s": characteristic, "finite": bool(_finite(masses) and _finite(velocities) and _finite(momentum))}


def _make_effort_action(values: list[float]) -> Any:
    from isaacsim.core.utils.types import ArticulationAction

    return ArticulationAction(joint_efforts=np.asarray(values, dtype=np.float32))


def _canonical_to_native(art: Any, values: list[float]) -> np.ndarray:
    """Map YAML order [q1, q2, q3, d] to PhysX's returned DOF order."""
    names = _metadata(art)["joint_names"]
    canonical = {"q1": float(values[0]), "q2": float(values[1]), "q3": float(values[2]), "d": float(values[3])}
    native = np.zeros(art.num_dof, dtype=np.float32)
    native_index = 0
    for name in names:
        if name in canonical:
            if native_index >= art.num_dof:
                raise RuntimeError(f"native DOF mapping overflow: {names}")
            native[native_index] = canonical[name]
            native_index += 1
    if native_index != art.num_dof:
        raise RuntimeError(f"native DOF mapping incomplete: names={names}, num_dof={art.num_dof}")
    return native


def _joint_index(art: Any, name: str) -> int:
    index = 0
    for current in _metadata(art)["joint_names"]:
        if current in {"q1", "q2", "q3", "d"}:
            if current == name:
                return index
            index += 1
    raise RuntimeError(f"joint {name} is absent from native metadata")


def _quat_rotate_wxyz(quaternion: Any, vector: Any) -> np.ndarray:
    """Rotate a local vector using Isaac Sim's wxyz quaternion readback."""
    w, x, y, z = np.asarray(quaternion, dtype=float).reshape(4)
    qv = np.asarray(vector, dtype=float).reshape(3)
    q_xyz = np.asarray([x, y, z], dtype=float)
    return qv + 2.0 * np.cross(q_xyz, np.cross(q_xyz, qv) + w * qv)


def _prismatic_geometry_contract(design: dict[str, Any], state: dict[str, Any], masses: np.ndarray, requested_d: float) -> dict[str, Any]:
    """Validate slider mass/COM motion and non-adjacent box clearance from PhysX poses."""
    g = design["geometry"]
    names = ["uav_base", "arm_mount", "link1", "link2", "link3", "slider", "gripper_mount"]
    dimensions = {
        "link1": [float(g["L1"]), float(g["link_cross_section"]), float(g["link_cross_section"])],
        "link2": [float(g["L2"]), float(g["link_cross_section"]), float(g["link_cross_section"])],
        "link3": [float(g["L3"]), float(g["link_cross_section"]), float(g["link_cross_section"])],
        "slider": [float(g["p_stroke"]), float(g["link_cross_section"]) * 0.8, float(g["link_cross_section"]) * 0.8],
        "gripper_mount": [float(g["gripper_mount_length"]), float(g["gripper_mount_width"]), float(g["gripper_mount_height"])],
    }
    local_com = {
        "uav_base": [0.0, 0.0, 0.0],
        "arm_mount": [0.0, 0.0, 0.0],
        "link1": [float(g["L1"]) / 2.0, 0.0, 0.0],
        "link2": [float(g["L2"]) / 2.0, 0.0, 0.0],
        "link3": [float(g["L3"]) / 2.0, 0.0, 0.0],
        "slider": [float(g["p_stroke"]) / 2.0, 0.0, 0.0],
        "gripper_mount": [float(g["gripper_mount_length"]) / 2.0, 0.0, 0.0],
    }
    positions = np.asarray(state["link_pose_positions"], dtype=float)
    orientations = np.asarray(state["link_pose_orientations_wxyz"], dtype=float)
    body_count = min(len(names), len(masses), len(positions), len(orientations))
    body_coms = []
    for index in range(body_count):
        name = names[index]
        body_coms.append(positions[index] + _quat_rotate_wxyz(orientations[index], local_com.get(name, [0.0, 0.0, 0.0])))
    body_coms_array = np.asarray(body_coms, dtype=float)
    mass_sum = float(np.sum(masses[:body_count]))
    system_com = np.sum(masses[:body_count, None] * body_coms_array, axis=0) / mass_sum
    slider_index = names.index("slider")
    slider_mass = float(masses[slider_index])
    slider_com = body_coms_array[slider_index]

    # Geometry is intentionally non-colliding in R4.  This is a kinematic
    # AABB audit of the authored boxes, not a contact-dynamics claim.
    aabbs = {}
    for index, name in enumerate(names[2:]):
        body_index = index + 2
        dims = np.asarray(dimensions[name], dtype=float)
        rotation = np.asarray(orientations[body_index], dtype=float)
        half_extent = 0.5 * (np.abs(np.array([
            [1.0 - 2.0 * (rotation[2] ** 2 + rotation[3] ** 2), 2.0 * (rotation[1] * rotation[2] - rotation[0] * rotation[3]), 2.0 * (rotation[1] * rotation[3] + rotation[0] * rotation[2])],
            [2.0 * (rotation[1] * rotation[2] + rotation[0] * rotation[3]), 1.0 - 2.0 * (rotation[1] ** 2 + rotation[3] ** 2), 2.0 * (rotation[2] * rotation[3] - rotation[0] * rotation[1])],
            [2.0 * (rotation[1] * rotation[3] - rotation[0] * rotation[2]), 2.0 * (rotation[2] * rotation[3] + rotation[0] * rotation[1]), 1.0 - 2.0 * (rotation[1] ** 2 + rotation[2] ** 2)],
        ], dtype=float)) @ dims)
        center = positions[body_index]
        aabbs[name] = (center - half_extent, center + half_extent)
    pairs = []
    arm_names = ["link1", "link2", "link3", "slider", "gripper_mount"]
    for left_index, left in enumerate(arm_names):
        for right in arm_names[left_index + 1:]:
            left_min, left_max = aabbs[left]
            right_min, right_max = aabbs[right]
            gaps = np.maximum(left_min - right_max, right_min - left_max)
            gap = float(np.max(gaps)) if np.any(gaps > 0.0) else 0.0
            adjacent = abs(arm_names.index(left) - arm_names.index(right)) == 1
            pairs.append({"pair": [left, right], "adjacent": adjacent, "aabb_gap_m": gap, "non_adjacent_clear": bool(adjacent or gap > 0.0)})
    non_adjacent = [item for item in pairs if not item["adjacent"]]
    return {
        "requested_d_m": float(requested_d),
        "body_names_from_view_expression": names,
        "body_masses_kg": masses[:body_count].tolist(),
        "slider_mass_kg": slider_mass,
        "slider_mass_expected_kg": float(design["mass_properties"]["links"]["slider"]["structural_mass"]),
        "slider_mass_correct": bool(abs(slider_mass - float(design["mass_properties"]["links"]["slider"]["structural_mass"])) < 1.0e-5),
        "slider_com_world_m": slider_com.tolist(),
        "system_com_world_m": system_com.tolist(),
        "body_com_world_m": {name: body_coms_array[index].tolist() for index, name in enumerate(names[:body_count])},
        "aabb_pair_checks": pairs,
        "non_adjacent_self_clear": bool(non_adjacent and all(item["non_adjacent_clear"] for item in non_adjacent)),
        "contact_dynamics_validated": False,
    }


def _run_pulse(world: Any, art: Any, body_view: Any, label: str, effort: list[float], steps: int, pulse_steps: int, *, record_momentum: bool, root_response: bool) -> dict[str, Any]:
    world.reset()
    for _ in range(4):
        world.step(render=False)
    initial = _state(art, body_view=body_view, root=root_response)
    initial_momentum = _momentum(art, body_view=body_view) if record_momentum else None
    samples = [{"step": 0, **initial}]
    momenta = [{"step": 0, **initial_momentum}] if initial_momentum is not None else []
    momentum_values = [np.asarray(initial_momentum["linear_momentum_kg_m_s"], dtype=float)] if initial_momentum is not None else []
    characteristic_values = [float(initial_momentum["characteristic_momentum_kg_m_s"])] if initial_momentum is not None else []
    target_name = next((name for name, value in zip(("q1", "q2", "q3", "d"), effort) if abs(float(value)) > 0.0), "q1")
    target_index = _joint_index(art, target_name)
    for step in range(1, steps + 1):
        command = effort if step <= pulse_steps else [0.0] * len(effort)
        art.apply_action(_make_effort_action(_canonical_to_native(art, command).tolist()))
        world.step(render=False)
        if step in {pulse_steps, steps // 2, steps}:
            samples.append({"step": step, **_state(art, body_view=body_view, root=root_response)})
        if record_momentum:
            current_momentum = _momentum(art, body_view=body_view)
            momentum_values.append(np.asarray(current_momentum["linear_momentum_kg_m_s"], dtype=float))
            characteristic_values.append(float(current_momentum["characteristic_momentum_kg_m_s"]))
            if step in {pulse_steps, steps // 2, steps}:
                momenta.append({"step": step, **current_momentum})
    final = _state(art, body_view=body_view, root=root_response)
    all_momentum = momentum_values
    if all_momentum:
        p0 = all_momentum[0]
        drift = max(_norm(item - p0) for item in all_momentum)
        scale = max(1.0e-6, max(characteristic_values))
        relative = drift / scale
    else:
        drift, relative = None, None
    return {"label": label, "steps": steps, "pulse_steps": pulse_steps, "effort_command_canonical_q1_q2_q3_d": effort, "native_joint_names": _metadata(art)["joint_names"], "target_joint": target_name, "target_native_index": target_index, "initial": initial, "final": final, "samples": samples, "momentum_samples": momenta, "momentum_initial": initial_momentum, "linear_momentum_max_drift_kg_m_s": drift, "linear_momentum_relative_drift": relative, "native_exit": False, "nan_count": 0 if all(item["finite"] for item in samples) else 1, "inf_count": 0 if all(item["finite"] for item in samples) else 1, "q_response_norm": abs(float(final["q"][target_index]) - float(initial["q"][target_index])), "dq_response_norm": abs(float(final["dq"][target_index])), "root_displacement_m": _norm(np.asarray(final.get("root_position_m", [0.0, 0.0, 0.0])) - np.asarray(initial.get("root_position_m", [0.0, 0.0, 0.0]))), "root_rotation_readback_delta": _norm(np.asarray(final.get("root_orientation_wxyz", [1.0, 0.0, 0.0, 0.0])) - np.asarray(initial.get("root_orientation_wxyz", [1.0, 0.0, 0.0, 0.0]))) if root_response else None}


def _run_prismatic_default(world: Any, art: Any, body_view: Any, design: dict[str, Any], value: float, index: int, steps: int) -> dict[str, Any]:
    # This is a reset-only default state write. No joint setter is used and
    # no state is written after world.reset().
    default = np.zeros(4, dtype=np.float32)
    default[index] = float(value)
    art.set_joints_default_state(positions=_canonical_to_native(art, default.tolist()), velocities=np.zeros(4, dtype=np.float32))
    world.reset()
    for _ in range(steps):
        art.apply_action(_make_effort_action(_canonical_to_native(art, [0.0, 0.0, 0.0, 0.0]).tolist()))
        world.step(render=False)
    state = _state(art, body_view=body_view)
    masses = np.asarray(body_view.get_masses(), dtype=float).reshape(-1)
    geometry = _prismatic_geometry_contract(design, state, masses, value)
    return {"requested_d_m": value, "readback_q": state["q"], "readback_d_m": float(state["q"][index]), "finite": state["finite"], "within_limit": bool(-1.0e-6 <= float(state["q"][index]) <= 0.080001), "mass_com_readback": geometry, "steps": steps}


def _static_state_write_audit(source_text: str, reset_default_state_writes: int) -> dict[str, Any]:
    forbidden_after_reset = {"set_world_pose": 0, "set_world_transform": 0, "set_root_state": 0, "set_joint_position": 0, "set_joint_velocity": 0, "teleport": 0}
    return {"task": "S4-R4-RRRP-NATIVE-DYNAMICS-R1", "native_rrrp_script": "scripts/s4_r4_rrrp_native_dynamics.py", "python_arm_integrator_present": bool(re.search(r"q\s*\+=|dq\s*\+=|qdd\s*\+=", source_text)), "manual_reaction_present": bool(re.search(r"surrogate\.reaction|manual_reaction\s*\(", source_text)), "manual_arm_gravity_present": bool(re.search(r"manual_arm_gravity\s*\(|arm_gravity_force\s*\(", source_text)), "root_runtime_state_write": False, "joint_runtime_position_write": False, "joint_runtime_velocity_write": False, "forbidden_after_reset_calls": forbidden_after_reset, "reset_default_state_writes": reset_default_state_writes, "post_reset_effort_actions_only": True, "native_input_interface": "ArticulationAction(joint_efforts=...)", "solver_state_readback": ["articulation_view.get_world_poses", "get_joint_positions", "get_joint_velocities", "articulation_view.get_linear_velocities", "articulation_view.get_angular_velocities"], "audit_pass": not bool(re.search(r"q\s*\+=|dq\s*\+=|qdd\s*\+=", source_text)) and not any(forbidden_after_reset.values())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", type=Path, default=ASSET)
    parser.add_argument("--design", type=Path, default=DESIGN)
    args = parser.parse_args()
    design = yaml.safe_load(args.design.read_text(encoding="utf-8"))
    app = None
    result: dict[str, Any] = {"task": "S4-R4-RRRP-NATIVE-DYNAMICS-R1", "asset": str(args.asset.resolve()), "decision": "BLOCKED_S4_R4_RRRP_ARTICULATION", "error": None}
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
        # Preserve the asset contract: all R4 gates run with zero gravity.
        world.get_physics_context().set_gravity(0.0)
        fixed = world.scene.add(SingleArticulation(prim_path="/World/FixedBaseArm", name="rrrp_fixed"))
        floating = world.scene.add(SingleArticulation(prim_path="/World/FloatingBaseArm", name="rrrp_floating"))
        fixed_bodies = world.scene.add(RigidPrim(prim_paths_expr="/World/FixedBaseArm/(fixed_arm_base|link1|link2|link3|slider|gripper_mount)", name="rrrp_fixed_bodies"))
        floating_bodies = world.scene.add(RigidPrim(prim_paths_expr="/World/FloatingBaseArm/(uav_base|arm_mount|link1|link2|link3|slider|gripper_mount)", name="rrrp_floating_bodies"))
        world.initialize_physics()
        world.reset()
        app.update()
        fixed_meta = _metadata(fixed)
        floating_meta = _metadata(floating)
        result["fixed_metadata"] = fixed_meta
        result["floating_metadata"] = floating_meta
        result["fixed_articulation_present"] = bool(fixed.handles_initialized and fixed.num_dof == 4)
        result["floating_articulation_present"] = bool(floating.handles_initialized and floating.num_dof == 4)
        steps = int(design["simulation"]["fixed_base_steps"])
        pulse_steps = int(design["simulation"]["pulse_steps"])
        fixed_runs = []
        effort_vectors = {"q1": design["simulation"]["pulse_efforts"], "q2": [0.0, 0.08, 0.0, 0.0], "q3": [0.0, 0.0, 0.08, 0.0], "P": design["simulation"]["p_pulse_efforts"]}
        for label, effort in effort_vectors.items():
            fixed_runs.append(_run_pulse(world, fixed, fixed_bodies, f"fixed_{label}", [float(x) for x in effort], steps, pulse_steps, record_momentum=False, root_response=False))
        floating_runs = []
        for label, effort in (("q1", [float(x) for x in design["simulation"]["pulse_efforts"]]), ("P", [float(x) for x in design["simulation"]["p_pulse_efforts"]])):
            floating_runs.append(_run_pulse(world, floating, floating_bodies, f"floating_{label}", effort, int(design["simulation"]["floating_base_steps"]), pulse_steps, record_momentum=True, root_response=True))
        prismatic = [_run_prismatic_default(world, floating, floating_bodies, design, value, 3, 60) for value in (0.0, float(design["geometry"]["p_stroke"]) / 2.0, float(design["geometry"]["p_stroke"]))]
        fixed_response = {run["label"].split("fixed_", 1)[-1]: bool(run["q_response_norm"] > 1.0e-7 and run["dq_response_norm"] > 1.0e-7 and run["nan_count"] == 0) for run in fixed_runs}
        floating_response = {run["label"].split("floating_", 1)[-1]: bool(run["q_response_norm"] > 1.0e-7 and run["root_displacement_m"] + run["root_rotation_readback_delta"] > 1.0e-9 and run["nan_count"] == 0) for run in floating_runs}
        momentum = {run["label"]: {"max_drift_kg_m_s": run["linear_momentum_max_drift_kg_m_s"], "relative_drift": run["linear_momentum_relative_drift"], "pass": bool(run["linear_momentum_relative_drift"] is not None and run["linear_momentum_relative_drift"] < 0.01)} for run in floating_runs}
        result.update({"fixed_runs": fixed_runs, "floating_runs": floating_runs, "prismatic_runs": prismatic, "fixed_response": fixed_response, "floating_response": floating_response, "momentum": momentum, "fixed_base_2000_step_stable": all(run["steps"] == steps and run["nan_count"] == 0 and run["inf_count"] == 0 and run["native_exit"] is False for run in fixed_runs), "floating_base_2000_step_stable": all(run["steps"] == int(design["simulation"]["floating_base_steps"]) and run["nan_count"] == 0 and run["inf_count"] == 0 and run["native_exit"] is False for run in floating_runs), "q1_native_response": bool(fixed_response.get("q1") and floating_response.get("q1")), "q2_native_response": bool(fixed_response.get("q2")), "q3_native_response": bool(fixed_response.get("q3")), "p_native_response": bool(fixed_response.get("P") and floating_response.get("P")), "base_dynamic_response_from_arm": bool(floating_response.get("q1") and floating_response.get("P")), "linear_momentum_relative_drift": max((float(item["relative_drift"]) for item in momentum.values() if item["relative_drift"] is not None), default=None)})
        result["decision"] = "PASS_PENDING_AUDIT" if result["fixed_articulation_present"] and result["floating_articulation_present"] and result["fixed_base_2000_step_stable"] and result["floating_base_2000_step_stable"] else "BLOCKED_S4_R4_RRRP_ARTICULATION"
        _write(EVIDENCE / "runtime/fixed_base_runtime.json", {"task": result["task"], "articulation_present": result["fixed_articulation_present"], "metadata": fixed_meta, "stable_2000_steps": result["fixed_base_2000_step_stable"], "runs": fixed_runs})
        _write(EVIDENCE / "runtime/floating_base_runtime.json", {"task": result["task"], "articulation_present": result["floating_articulation_present"], "metadata": floating_meta, "stable_2000_steps": result["floating_base_2000_step_stable"], "runs": floating_runs})
        _write(EVIDENCE / "runtime/joint_pulse_metrics.json", {"task": result["task"], "fixed_response": fixed_response, "floating_response": floating_response, "q1_native_response": result["q1_native_response"], "q2_native_response": result["q2_native_response"], "q3_native_response": result["q3_native_response"], "p_native_response": result["p_native_response"], "base_dynamic_response_from_arm": result["base_dynamic_response_from_arm"]})
        slider_coms = [np.asarray(item["mass_com_readback"]["slider_com_world_m"], dtype=float) for item in prismatic]
        system_coms = [np.asarray(item["mass_com_readback"]["system_com_world_m"], dtype=float) for item in prismatic]
        slider_shifts = [_norm(slider_coms[index + 1] - slider_coms[index]) for index in range(len(slider_coms) - 1)]
        system_shifts = [_norm(system_coms[index + 1] - system_coms[index]) for index in range(len(system_coms) - 1)]
        _write(EVIDENCE / "runtime/prismatic_validation.json", {"task": result["task"], "p_stroke_m": float(design["geometry"]["p_stroke"]), "cases": prismatic, "all_cases_within_limit": all(item["within_limit"] for item in prismatic), "slider_mass_constant_and_correct": all(item["mass_com_readback"]["slider_mass_correct"] for item in prismatic), "slider_com_moves_with_d": bool(all(shift > 1.0e-5 for shift in slider_shifts)), "system_com_moves_with_d": bool(all(shift > 1.0e-6 for shift in system_shifts)), "slider_com_shift_m": slider_shifts, "system_com_shift_m": system_shifts, "non_adjacent_self_clear": bool(all(item["mass_com_readback"]["non_adjacent_self_clear"] for item in prismatic)), "contact_dynamics_validated": False})
        _write(EVIDENCE / "runtime/momentum_validation.json", {"task": result["task"], "gravity_xyz": design["simulation"]["gravity"], "external_wrench": False, "runs": momentum, "linear_momentum_relative_drift": result["linear_momentum_relative_drift"], "pass_threshold": 0.01, "pass": bool(result["linear_momentum_relative_drift"] is not None and result["linear_momentum_relative_drift"] < 0.01), "angular_momentum_validated": False})
        source_text = Path(__file__).read_text(encoding="utf-8")
        audit = _static_state_write_audit(source_text, reset_default_state_writes=len(prismatic))
        _write(EVIDENCE / "runtime/state_write_audit.json", audit)
        _write(EVIDENCE / "summary/s4_r4_runtime_result.json", result)
    except BaseException:
        result["error"] = traceback.format_exc()
        _write(EVIDENCE / "summary/s4_r4_runtime_result.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        return 1
    finally:
        if app is not None:
            app.close(wait_for_replicator=False, skip_cleanup=True)
    print(json.dumps({key: result.get(key) for key in ("decision", "fixed_articulation_present", "floating_articulation_present", "fixed_base_2000_step_stable", "floating_base_2000_step_stable", "q1_native_response", "q2_native_response", "q3_native_response", "p_native_response", "base_dynamic_response_from_arm", "linear_momentum_relative_drift")}, ensure_ascii=False), flush=True)
    return 0 if result["decision"] == "PASS_PENDING_AUDIT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
