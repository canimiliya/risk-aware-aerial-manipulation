from __future__ import annotations

import numpy as np

from planner_bridge.execution.full_body_proxy import T_B_A0


# The source trajectory only carries an equivalent horizontal tool-direction
# constraint.  This representative A0 axis is deliberately not a complete EE
# orientation and is stored as a direction, never as an end-effector quaternion.
TOOL_DIRECTION_A0 = np.asarray([1.0, 0.0, 0.0], dtype=float)


def normalize_quaternion_wxyz(quaternion: np.ndarray) -> np.ndarray:
    q = np.asarray(quaternion, dtype=float)
    norm = float(np.linalg.norm(q))
    if norm == 0.0 or not np.isfinite(norm):
        raise ValueError("quaternion must be finite and non-zero")
    return q / norm


def normalize_quaternion_xyzw(quaternion: np.ndarray) -> np.ndarray:
    """Compatibility helper for older callers; the protocol is WXYZ."""
    q = np.asarray(quaternion, dtype=float)
    norm = float(np.linalg.norm(q))
    if norm == 0.0 or not np.isfinite(norm):
        raise ValueError("quaternion must be finite and non-zero")
    return q / norm


def rotation_from_quaternion_wxyz(quaternion: np.ndarray) -> np.ndarray:
    w, x, y, z = map(float, normalize_quaternion_wxyz(quaternion))
    return np.asarray(
        [
            [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
            [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
            [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
        ],
        dtype=float,
    )


def compose_world_ee(
    base_position: np.ndarray,
    arm_position_a0: np.ndarray,
    base_rotation_wb: np.ndarray | None = None,
    transform_b_a0: np.ndarray = T_B_A0,
) -> np.ndarray:
    """Compose ``p_WE = p_WB + R_WB (R_BA0 p_A0E + t_BA0)``."""
    p_wb = np.asarray(base_position, dtype=float)
    p_a0 = np.asarray(arm_position_a0, dtype=float)
    rotation_wb = np.eye(3) if base_rotation_wb is None else np.asarray(base_rotation_wb, dtype=float)
    transform = np.asarray(transform_b_a0, dtype=float)
    if transform.shape != (4, 4) or rotation_wb.shape != (3, 3):
        raise ValueError("invalid B->A0 or base rotation shape")
    return p_wb + rotation_wb @ (transform[:3, :3] @ p_a0 + transform[:3, 3])


def transform_tool_direction(
    base_rotation_wb: np.ndarray,
    direction_a0: np.ndarray = TOOL_DIRECTION_A0,
    transform_b_a0: np.ndarray = T_B_A0,
) -> np.ndarray:
    direction = np.asarray(base_rotation_wb, dtype=float) @ np.asarray(transform_b_a0, dtype=float)[:3, :3] @ np.asarray(direction_a0, dtype=float)
    norm = float(np.linalg.norm(direction))
    if not np.isfinite(norm) or norm == 0.0:
        raise ValueError("tool direction must be finite and non-zero")
    return direction / norm
