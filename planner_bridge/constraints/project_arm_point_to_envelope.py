"""Project diagnostic violation states to official FK-generated feasible points."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from planner_bridge.execution.full_body_proxy import component_clearances, obstacle_tree
from planner_bridge.execution.official_delta_kinematics import official_fk_joint_state, official_joint_points, joint_margin


LOWER = np.array([0.02, 0.05, 0.02], dtype=float)
UPPER = np.array([math.pi / 2.0 - 0.02] * 3, dtype=float)


def project_joint_state(q: np.ndarray) -> np.ndarray:
    """Return a feasible target q used only to generate a fixed mode-3 point."""
    return np.minimum(np.maximum(np.asarray(q, dtype=float), LOWER), UPPER)


def project_event(event: dict[str, Any], variant: str = "nominal", clearance_gate_m: float = 0.010) -> dict[str, Any]:
    q_source = np.asarray(event["q_rad"], dtype=float)
    q_target = project_joint_state(q_source)
    arm_point = official_fk_joint_state(q_target)
    base_point = np.asarray(event["base_position_WB_m"], dtype=float)
    joint_points = official_joint_points(arm_point, q_target)
    clearances = component_clearances(base_point, np.eye(3), arm_point, joint_points, obstacle_tree(variant))
    minimum = float(min(clearances.values()))
    if minimum < clearance_gate_m:
        raise ValueError(f"projected point fails static full-body gate: {minimum}")
    return {
        "source_time_s": float(event["time_s"]),
        "source_segment_id": int(event["segment_id"]),
        "source_segment_local_time_s": float(event["segment_local_time_s"]),
        "source_q_rad": q_source.tolist(),
        "target_q_rad": q_target.tolist(),
        "target_joint_margin_rad": float(joint_margin(q_target)),
        "base_point_WB_m": base_point.tolist(),
        "arm_point_A0_m": arm_point.tolist(),
        "static_full_body_clearance_m": minimum,
        "static_clearance_components_m": {key: float(value) for key, value in clearances.items()},
        "projection_is_constraint_only": True,
        "projection_is_not_output_trajectory": True,
    }
