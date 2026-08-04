from __future__ import annotations

import math
from typing import Any


REQUIRED = (
    "time", "base_position_m", "base_quaternion_xyzw", "base_velocity_m_s",
    "base_acceleration_m_s2", "base_jerk_m_s3", "body_angular_velocity_rad_s",
    "arm_cartesian_position_m", "arm_cartesian_velocity_m_s", "arm_cartesian_acceleration_m_s2",
    "q_rad", "qdot_rad_s", "qddot_rad_s2", "world_ee_position_m", "tool_direction_status",
    "phase_id", "phase_progress",
)


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if bundle.get("protocol") != "S3-R0-trajectory-protocol-v1":
        errors.append("protocol")
    frames = bundle.get("frames", [])
    if not frames:
        errors.append("frames_empty")
        return errors
    last = -math.inf
    for index, frame in enumerate(frames):
        missing = [key for key in REQUIRED if key not in frame]
        errors.extend(f"frame_{index}_{key}" for key in missing)
        if missing:
            continue
        time = float(frame["time"])
        if not math.isfinite(time) or time < last:
            errors.append(f"time_{index}")
        last = time
        if frame["tool_direction_status"] != "EQUIVALENT_HORIZONTAL_DIRECTION_CONSTRAINT":
            errors.append(f"tool_direction_status_{index}")
        quaternion = frame["base_quaternion_xyzw"]
        if len(quaternion) != 4 or abs(sum(float(x) ** 2 for x in quaternion) - 1.0) > 1e-9:
            errors.append(f"quaternion_{index}")
        for key in REQUIRED[1:14]:
            if not all(math.isfinite(float(value)) for value in frame[key]):
                errors.append(f"finite_{index}_{key}")
    return errors
