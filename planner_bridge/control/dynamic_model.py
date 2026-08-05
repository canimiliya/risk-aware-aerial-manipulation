"""Route-B arm reaction surrogate with an analytic COM acceleration contract."""

from __future__ import annotations

import numpy as np


class ArmReactionSurrogate:
    """COM-only arm reaction model used only for the S4-R0 nominal proof.

    The COM map is expressed in the base body frame.  Internal arm reaction
    is computed from the exact kinematic identity ``a = J qdd + Jdot dq``;
    no state history or first-frame finite-difference pulse is used.
    rotational inertia is intentionally not part of this interface because the
    route-B model does not claim a full articulated rotational dynamics model.
    """

    mode = "BASE_DYNAMIC_ARM_REACTION_SURROGATE_V1"
    full_closed_chain_dynamics = False
    dynamic_surrogate = True

    acceleration_contract = "ANALYTIC_COM_J_QDD_PLUS_JDOT_DQ"
    reaction_scope = "COM_TRANSLATIONAL_ONLY"

    def __init__(self, arm_mass_kg: float, com_offset_m: np.ndarray) -> None:
        self.arm_mass_kg = float(arm_mass_kg)
        self.com_offset_m = np.asarray(com_offset_m, dtype=float)
        if not np.isfinite(self.arm_mass_kg) or self.arm_mass_kg <= 0.0:
            raise ValueError("arm_mass_kg must be finite and positive")

    def com(self, q: np.ndarray, q_ref: np.ndarray | None = None) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        # Smooth, bounded COM map derived from the three active joint axes.
        return self.com_offset_m + np.array([
            0.055 * np.sin(q[0]) - 0.030 * np.sin(q[1]),
            0.045 * np.sin(q[1]) - 0.025 * np.sin(q[2]),
            0.030 * (np.cos(q).sum() - 3.0),
        ])

    def jacobian(self, q: np.ndarray) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        if q.shape != (3,):
            raise ValueError(f"q must have shape (3,), got {q.shape}")
        return np.asarray([
            [0.055 * np.cos(q[0]), -0.030 * np.cos(q[1]), 0.0],
            [0.0, 0.045 * np.cos(q[1]), -0.025 * np.cos(q[2])],
            [-0.030 * np.sin(q[0]), -0.030 * np.sin(q[1]), -0.030 * np.sin(q[2])],
        ], dtype=float)

    def jacobian_dot(self, q: np.ndarray, dq: np.ndarray) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        dq = np.asarray(dq, dtype=float)
        if q.shape != (3,) or dq.shape != (3,):
            raise ValueError("q and dq must both have shape (3,)")
        return np.asarray([
            [-0.055 * np.sin(q[0]) * dq[0], 0.030 * np.sin(q[1]) * dq[1], 0.0],
            [0.0, -0.045 * np.sin(q[1]) * dq[1], 0.025 * np.sin(q[2]) * dq[2]],
            [-0.030 * np.cos(q[0]) * dq[0], -0.030 * np.cos(q[1]) * dq[1], -0.030 * np.cos(q[2]) * dq[2]],
        ], dtype=float)

    def reaction(self, q: np.ndarray, dq: np.ndarray, qdd: np.ndarray, base_rotation: np.ndarray | None = None) -> dict[str, np.ndarray | float | bool]:
        q = np.asarray(q, dtype=float)
        dq = np.asarray(dq, dtype=float)
        qdd = np.asarray(qdd, dtype=float)
        if q.shape != (3,) or dq.shape != (3,) or qdd.shape != (3,):
            raise ValueError("q, dq, and qdd must all have shape (3,)")
        current_com = self.com(q)
        jacobian = self.jacobian(q)
        jacobian_dot = self.jacobian_dot(q, dq)
        velocity_body = jacobian @ dq
        acceleration_body = jacobian @ qdd + jacobian_dot @ dq
        force_body = -self.arm_mass_kg * acceleration_body
        torque_body = -np.cross(current_com, self.arm_mass_kg * acceleration_body)
        rotation = np.eye(3) if base_rotation is None else np.asarray(base_rotation, dtype=float)
        force_world = rotation @ force_body
        torque_world = rotation @ torque_body
        finite = bool(np.isfinite(np.concatenate((current_com, velocity_body, acceleration_body, force_body, torque_body))).all())
        return {
            "com_m": current_com,
            "jacobian": jacobian,
            "jacobian_dot": jacobian_dot,
            "velocity_m_s": velocity_body,
            "acceleration_m_s2": acceleration_body,
            "force_body_N": force_body,
            "torque_body_Nm": torque_body,
            "force_world_N": force_world,
            "torque_world_Nm": torque_world,
            "finite": finite,
            "nonzero": bool(np.linalg.norm(force_body) > 1e-9 or np.linalg.norm(torque_body) > 1e-9),
        }
