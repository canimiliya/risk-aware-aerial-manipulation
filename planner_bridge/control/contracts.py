"""Small NumPy-only control contracts used by S4-R0."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np


def clamp_norm(value: np.ndarray, limit: float) -> tuple[np.ndarray, bool]:
    value = np.asarray(value, dtype=float)
    norm = float(np.linalg.norm(value))
    if norm <= limit or norm == 0.0:
        return value.copy(), False
    return value * (limit / norm), True


def quat_wxyz_to_rotation(q: np.ndarray) -> np.ndarray:
    w, x, y, z = np.asarray(q, dtype=float)
    n = float(np.linalg.norm([w, x, y, z]))
    if n == 0.0:
        return np.eye(3)
    w, x, y, z = np.asarray([w, x, y, z], dtype=float) / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def rotation_error_vector(reference: np.ndarray, actual: np.ndarray) -> np.ndarray:
    """Return the small-angle SO(3) error used by the inner loop."""

    return 0.5 * (
        np.cross(actual[:, 0], reference[:, 0])
        + np.cross(actual[:, 1], reference[:, 1])
        + np.cross(actual[:, 2], reference[:, 2])
    )


@dataclass(frozen=True)
class WrenchCommand:
    raw_force_world: np.ndarray
    clipped_force_world: np.ndarray
    raw_torque_body: np.ndarray
    clipped_torque_body: np.ndarray
    force_saturated: bool
    torque_saturated: bool


@dataclass(frozen=True)
class JointCommand:
    q_ref: np.ndarray
    dq_ref: np.ndarray
    effort_raw: np.ndarray
    effort_clipped: np.ndarray
    saturated: np.ndarray
