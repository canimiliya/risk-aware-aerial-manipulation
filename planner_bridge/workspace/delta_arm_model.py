from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class DeltaArmParameters:
    static_radius_m: float = 0.08
    moving_radius_m: float = 0.025
    upper_arm_m: float = 0.10
    lower_arm_m: float = 0.16
    joint_lower_rad: float = -1.57
    joint_upper_rad: float = 1.57
    scale: float = 1.0


class DeltaArmModel:
    """Official AM-Planner delta-display FK with the launch geometry values."""

    def __init__(self, params: DeltaArmParameters | None = None) -> None:
        self.params = params or DeltaArmParameters()
        p = self.params
        self.phi = np.array([math.pi / 6.0, 5.0 * math.pi / 6.0, 3.0 * math.pi / 2.0])

    @property
    def joint_lower(self) -> np.ndarray:
        return np.full(3, self.params.joint_lower_rad, dtype=float)

    @property
    def joint_upper(self) -> np.ndarray:
        return np.full(3, self.params.joint_upper_rad, dtype=float)

    def _check_q(self, q: np.ndarray) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        if q.shape != (3,):
            raise ValueError(f"q must have shape (3,), got {q.shape}")
        if not np.all(np.isfinite(q)):
            raise ValueError("q contains NaN/Inf")
        return q

    def fk(self, q: np.ndarray) -> np.ndarray:
        """Return moving-platform center in the AM-Planner A0 frame.

        This is a direct NumPy transcription of delta_display.cpp::FK_kin;
        no alternate DH model is substituted.
        """
        theta1, theta2, theta3 = self._check_q(q)
        p = self.params
        static_r = p.static_radius_m * p.scale
        moving_r = p.moving_radius_m * p.scale
        upper = p.upper_arm_m * p.scale
        lower = p.lower_arm_m * p.scale
        a1 = math.sqrt(3.0) / 2.0 * (static_r + upper * math.sin(theta1) - moving_r)
        b1 = (static_r + upper * math.sin(theta1) - moving_r) / 2.0
        c1 = upper * math.cos(theta1)
        a2 = -math.sqrt(3.0) / 2.0 * (static_r + upper * math.sin(theta2) - moving_r)
        b2 = (static_r + upper * math.sin(theta2) - moving_r) / 2.0
        c2 = upper * math.cos(theta2)
        b3 = static_r + upper * math.sin(theta3) - moving_r
        c3 = upper * math.cos(theta3)
        d1 = (a1 * a1 + b1 * b1 + c1 * c1 - b3 * b3 - c3 * c3) / 2.0
        d2 = (a2 * a2 + b2 * b2 + c2 * c2 - b3 * b3 - c3 * c3) / 2.0
        b13, c13 = b1 + b3, c1 - c3
        b23, c23 = b2 + b3, c2 - c3
        denom = a2 * b13 - a1 * b23
        if abs(denom) < 1e-12:
            raise ValueError("singular closed-chain elimination denominator")
        e2 = (a2 * c13 - a1 * c23) / denom
        f2 = (a2 * d1 - a1 * d2) / denom
        e1 = (b13 * c23 - b23 * c13) / denom
        f1 = (b13 * d2 - b23 * d1) / denom
        aa = e1 * e1 + e2 * e2 + 1.0
        bb = 2.0 * e2 * f2 + 2.0 * b3 * e2 + 2.0 * e1 * f1 + 2.0 * c3
        cc = f2 * f2 + b3 * b3 + 2.0 * b3 * f2 + f1 * f1 + c3 * c3 - lower * lower
        discriminant = bb * bb - 4.0 * aa * cc
        if discriminant < -1e-10:
            raise ValueError(f"closed-chain discriminant is negative: {discriminant}")
        z = (-bb - math.sqrt(max(discriminant, 0.0))) / (2.0 * aa)
        return np.array([e1 * z + f1, e2 * z + f2, z], dtype=float)

    def fk_batch(self, qs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        qs = np.asarray(qs, dtype=float)
        positions = np.full((len(qs), 3), np.nan, dtype=float)
        valid = np.zeros(len(qs), dtype=bool)
        for i, q in enumerate(qs):
            try:
                positions[i] = self.fk(q)
                valid[i] = True
            except ValueError:
                pass
        return positions, valid

    def ik(self, position: np.ndarray) -> np.ndarray:
        """Official delta-display.cpp::IK_kin branch, for candidate pose checks."""
        x, y, z = np.asarray(position, dtype=float)
        p = self.params
        lower, upper = p.lower_arm_m * p.scale, p.upper_arm_m * p.scale
        d = (p.static_radius_m - p.moving_radius_m) * p.scale
        middle = lower * lower - upper * upper - (x * x + y * y + z * z) - d * d
        k1 = 2 * z + (middle + d * (math.sqrt(3.0) * x + y)) / upper
        u1 = -2 * (2 * d - math.sqrt(3.0) * x - y)
        v1 = -4 * z + k1
        k2 = 2 * z + (middle - d * (math.sqrt(3.0) * x - y)) / upper
        u2 = -2 * (2 * d + math.sqrt(3.0) * x - y)
        v2 = -4 * z + k2
        k3 = z + (middle - 2 * y * d) / (2 * upper)
        u3 = -2 * (d + y)
        v3 = -2 * z + k3
        values = []
        for k, u, v in [(k1, u1, v1), (k2, u2, v2), (k3, u3, v3)]:
            disc = u * u - 4 * k * v
            if abs(k) < 1e-12 or disc < -1e-10:
                raise ValueError("unreachable inverse-kinematics pose")
            t = (-u - math.sqrt(max(disc, 0.0))) / (2 * k)
            values.append(math.pi / 2 - 2 * math.atan(t))
        q = np.array(values, dtype=float)
        if np.any(q < self.joint_lower - 1e-8) or np.any(q > self.joint_upper + 1e-8):
            raise ValueError("IK solution violates official joint limits")
        return q

    def link_points(self, q: np.ndarray) -> dict[str, np.ndarray]:
        """Return source getJointPoints-style A/B/C points and collision segments."""
        q = self._check_q(q)
        p = self.params
        R = p.static_radius_m * p.scale
        r = p.moving_radius_m * p.scale
        L = p.upper_arm_m * p.scale
        e = self.fk(q)
        A = np.column_stack((R * np.cos(self.phi), R * np.sin(self.phi), np.zeros(3)))
        B = A + np.column_stack((L * np.cos(q) * np.cos(self.phi), L * np.cos(q) * np.sin(self.phi), -L * np.sin(q)))
        C = e[None, :] + np.column_stack((r * np.cos(self.phi), r * np.sin(self.phi), np.zeros(3)))
        return {"A": A, "B": B, "C": C, "upper_segments": np.stack([A, B], axis=1), "lower_segments": np.stack([B, C], axis=1)}

    def jacobian(self, q: np.ndarray, step: float = 1e-6) -> np.ndarray:
        q = self._check_q(q)
        jac = np.empty((3, 3), dtype=float)
        for j in range(3):
            plus, minus = q.copy(), q.copy()
            plus[j] += step
            minus[j] -= step
            jac[:, j] = (self.fk(plus) - self.fk(minus)) / (2.0 * step)
        return jac

    def normalized_joint_margin(self, q: np.ndarray) -> float:
        q = self._check_q(q)
        lower = (q - self.joint_lower) / (self.joint_upper - self.joint_lower)
        upper = (self.joint_upper - q) / (self.joint_upper - self.joint_lower)
        return float(np.min(np.concatenate([lower, upper])))
