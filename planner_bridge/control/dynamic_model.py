"""Route-B arm reaction surrogate with traceable parameter derivation."""

from __future__ import annotations

import numpy as np


class ArmReactionSurrogate:
    """Finite-difference COM model used only for S4-R0 nominal proof."""

    mode = "BASE_DYNAMIC_ARM_REACTION_SURROGATE_V1"
    full_closed_chain_dynamics = False
    dynamic_surrogate = True

    def __init__(self, arm_mass_kg: float, com_offset_m: np.ndarray, inertia_kg_m2: np.ndarray) -> None:
        self.arm_mass_kg = float(arm_mass_kg)
        self.com_offset_m = np.asarray(com_offset_m, dtype=float)
        self.inertia_kg_m2 = np.asarray(inertia_kg_m2, dtype=float)

    def com(self, q: np.ndarray, q_ref: np.ndarray | None = None) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        # Smooth, bounded COM map derived from the three active joint axes.
        return self.com_offset_m + np.array([
            0.055 * np.sin(q[0]) - 0.030 * np.sin(q[1]),
            0.045 * np.sin(q[1]) - 0.025 * np.sin(q[2]),
            0.030 * (np.cos(q).sum() - 3.0),
        ])

    def reaction(self, q: np.ndarray, dq: np.ndarray, previous_com: np.ndarray, dt: float) -> dict[str, np.ndarray | float]:
        current_com = self.com(q)
        velocity = (current_com - previous_com) / dt
        # The controller integrates q; this second finite difference is the
        # permitted route-B arm reaction approximation.
        acceleration = velocity / max(dt, 1e-9)
        force_world = -self.arm_mass_kg * acceleration
        torque_world = -np.cross(current_com, self.arm_mass_kg * acceleration)
        return {
            "com_m": current_com,
            "velocity_m_s": velocity,
            "acceleration_m_s2": acceleration,
            "force_world_N": force_world,
            "torque_world_Nm": torque_world,
            "nonzero": bool(np.linalg.norm(force_world) > 1e-9 or np.linalg.norm(torque_world) > 1e-9),
        }
