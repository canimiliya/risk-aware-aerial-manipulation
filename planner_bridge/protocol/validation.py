from __future__ import annotations

import math
from typing import Any

import numpy as np

from planner_bridge.execution.full_body_proxy import T_B_A0
from planner_bridge.protocol.frames import rotation_from_quaternion_wxyz


REQUIRED = (
    "time",
    "base_position_m",
    "base_quaternion_WB_wxyz",
    "base_velocity_m_s",
    "base_acceleration_m_s2",
    "base_jerk_m_s3",
    "base_body_omega_B_rad_s",
    "base_thrust_N",
    "arm_cartesian_position_m",
    "arm_cartesian_velocity_m_s",
    "arm_cartesian_acceleration_m_s2",
    "q_rad",
    "qdot_rad_s",
    "qddot_rad_s2",
    "world_ee_position_m",
    "tool_direction_status",
    "tool_direction_A0",
    "tool_direction_W",
    "phase_id",
    "phase_progress",
)
VECTOR_LENGTHS = {
    "base_position_m": 3,
    "base_quaternion_WB_wxyz": 4,
    "base_velocity_m_s": 3,
    "base_acceleration_m_s2": 3,
    "base_jerk_m_s3": 3,
    "base_body_omega_B_rad_s": 3,
    "arm_cartesian_position_m": 3,
    "arm_cartesian_velocity_m_s": 3,
    "arm_cartesian_acceleration_m_s2": 3,
    "q_rad": 3,
    "qdot_rad_s": 3,
    "qddot_rad_s2": 3,
    "world_ee_position_m": 3,
    "tool_direction_A0": 3,
    "tool_direction_W": 3,
}


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if bundle.get("protocol") != "S3-R0-trajectory-protocol-v1":
        errors.append("protocol")
    if bundle.get("sample_hz") != 200:
        errors.append("sample_hz")
    contract = bundle.get("scene_contract", {})
    if contract.get("base_quaternion_order") != "wxyz":
        errors.append("quaternion_order")
    if contract.get("world_ee") != "p_WB_plus_R_WB_(R_BA0_p_A0E_plus_t_BA0)":
        errors.append("world_ee_contract")
    frames = bundle.get("frames", [])
    if not frames:
        errors.append("frames_empty")
        return errors
    last = -math.inf
    dynamic_attitude = False
    for index, frame in enumerate(frames):
        missing = [key for key in REQUIRED if key not in frame]
        errors.extend(f"frame_{index}_{key}" for key in missing)
        if missing:
            continue
        time = float(frame["time"])
        if not math.isfinite(time) or time <= last:
            errors.append(f"time_{index}")
        last = time
        if frame["tool_direction_status"] != "EQUIVALENT_HORIZONTAL_DIRECTION_CONSTRAINT":
            errors.append(f"tool_direction_status_{index}")
        for key, length in VECTOR_LENGTHS.items():
            value = frame[key]
            if len(value) != length:
                errors.append(f"length_{index}_{key}")
                continue
            if not all(math.isfinite(float(item)) for item in value):
                errors.append(f"finite_{index}_{key}")
        for key in ("base_thrust_N", "phase_progress"):
            if not math.isfinite(float(frame[key])):
                errors.append(f"finite_{index}_{key}")
        try:
            quaternion = np.asarray(frame["base_quaternion_WB_wxyz"], dtype=float)
            norm_error = abs(float(np.linalg.norm(quaternion)) - 1.0)
            rotation = rotation_from_quaternion_wxyz(quaternion)
            orth_error = float(np.linalg.norm(rotation.T @ rotation - np.eye(3)))
            determinant = float(np.linalg.det(rotation))
        except (TypeError, ValueError, FloatingPointError):
            continue
        if norm_error > 1e-12:
            errors.append(f"quaternion_norm_{index}")
        if orth_error > 1e-10:
            errors.append(f"rotation_orthogonality_{index}")
        if abs(determinant - 1.0) > 1e-10:
            errors.append(f"rotation_determinant_{index}")
        if float(frame["base_thrust_N"]) <= 0.0:
            errors.append(f"thrust_{index}")
        direction_a0 = np.asarray(frame["tool_direction_A0"], dtype=float)
        direction_w = np.asarray(frame["tool_direction_W"], dtype=float)
        if abs(float(np.linalg.norm(direction_a0)) - 1.0) > 1e-12 or abs(float(np.linalg.norm(direction_w)) - 1.0) > 1e-12:
            errors.append(f"tool_direction_norm_{index}")
        if not np.allclose(direction_w, rotation @ T_B_A0[:3, :3] @ direction_a0, atol=1e-10, rtol=0.0):
            errors.append(f"tool_direction_transform_{index}")
        if not np.allclose(quaternion, np.asarray([1.0, 0.0, 0.0, 0.0]), atol=1e-12, rtol=0.0) or np.linalg.norm(np.asarray(frame["base_body_omega_B_rad_s"], dtype=float)) > 1e-12:
            dynamic_attitude = True
    if not dynamic_attitude:
        errors.append("identity_attitude_rejected")
    return errors
