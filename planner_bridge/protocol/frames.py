from __future__ import annotations

import numpy as np


def normalize_quaternion_xyzw(quaternion: np.ndarray) -> np.ndarray:
    q = np.asarray(quaternion, dtype=float)
    norm = float(np.linalg.norm(q))
    if norm == 0.0 or not np.isfinite(norm):
        raise ValueError("quaternion must be finite and non-zero")
    return q / norm


def compose_world_ee(base_position: np.ndarray, arm_position_a0: np.ndarray) -> np.ndarray:
    """S3 scene contract: A0 coincides with the base reference origin."""
    return np.asarray(base_position, dtype=float) + np.asarray(arm_position_a0, dtype=float)
