from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProtocolFrame:
    """One reference-state sample; all metric quantities are SI units."""

    time: float
    base_position: tuple[float, float, float]
    base_quaternion_WB_wxyz: tuple[float, float, float, float]
    base_velocity: tuple[float, float, float]
    base_acceleration: tuple[float, float, float]
    base_jerk: tuple[float, float, float]
    base_body_omega_B_rad_s: tuple[float, float, float]
    base_thrust_N: float
    arm_cartesian_position: tuple[float, float, float]
    arm_cartesian_velocity: tuple[float, float, float]
    arm_cartesian_acceleration: tuple[float, float, float]
    q: tuple[float, float, float]
    qdot: tuple[float, float, float]
    qddot: tuple[float, float, float]
    world_ee_position: tuple[float, float, float]
    tool_direction_status: str
    tool_direction_A0: tuple[float, float, float]
    tool_direction_W: tuple[float, float, float]
    phase_id: int
    phase_progress: float


def frame_from_mapping(value: dict[str, Any]) -> ProtocolFrame:
    return ProtocolFrame(
        time=float(value["time"]),
        base_position=tuple(value["base_position_m"]),
        base_quaternion_WB_wxyz=tuple(value["base_quaternion_WB_wxyz"]),
        base_velocity=tuple(value["base_velocity_m_s"]),
        base_acceleration=tuple(value["base_acceleration_m_s2"]),
        base_jerk=tuple(value["base_jerk_m_s3"]),
        base_body_omega_B_rad_s=tuple(value["base_body_omega_B_rad_s"]),
        base_thrust_N=float(value["base_thrust_N"]),
        arm_cartesian_position=tuple(value["arm_cartesian_position_m"]),
        arm_cartesian_velocity=tuple(value["arm_cartesian_velocity_m_s"]),
        arm_cartesian_acceleration=tuple(value["arm_cartesian_acceleration_m_s2"]),
        q=tuple(value["q_rad"]),
        qdot=tuple(value["qdot_rad_s"]),
        qddot=tuple(value["qddot_rad_s2"]),
        world_ee_position=tuple(value["world_ee_position_m"]),
        tool_direction_status=str(value["tool_direction_status"]),
        tool_direction_A0=tuple(value["tool_direction_A0"]),
        tool_direction_W=tuple(value["tool_direction_W"]),
        phase_id=int(value["phase_id"]),
        phase_progress=float(value["phase_progress"]),
    )
