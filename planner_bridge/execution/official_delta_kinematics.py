from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DeltaGeometry:
    """Official DeltaDisplay constructor geometry at scale=1."""

    # run_in_sim_grasp.launch overrides the DeltaDisplay constructor defaults
    # to these values in the captured AM-Planner execution.
    static_radius_m: float = 0.080
    moving_radius_m: float = 0.025
    upper_arm_m: float = 0.100
    lower_arm_m: float = 0.160
    scale: float = 1.0

    @property
    def R(self) -> float:
        return self.static_radius_m * self.scale

    @property
    def r(self) -> float:
        return self.moving_radius_m * self.scale

    @property
    def L(self) -> float:
        return self.upper_arm_m * self.scale

    @property
    def l(self) -> float:
        return self.lower_arm_m * self.scale


PHI = np.array([math.pi / 6.0, 5.0 * math.pi / 6.0, 3.0 * math.pi / 2.0])


def official_ik(point_a0: np.ndarray, geometry: DeltaGeometry = DeltaGeometry()) -> np.ndarray:
    """Exact project-owned translation of DeltaDisplay::IK_kin.

    The C++ definition uses (x1, y1, z1), while the header names the first
    two parameters (y, x).  Calls are validated in the definition/callback
    order x, y, z and this wrapper follows that numerical convention.
    """
    x1, y1, z1 = (float(v) * geometry.scale for v in np.asarray(point_a0, dtype=float))
    lower_arm = geometry.l
    static_r = geometry.R
    moving_r = geometry.r
    upper_arm = geometry.L
    position = np.array([x1, y1, z1], dtype=float)
    middle = lower_arm**2 - upper_arm**2 - float(position @ position) - (static_r - moving_r) ** 2

    k1 = 2.0 * z1 + (middle + (static_r - moving_r) * (math.sqrt(3.0) * x1 + y1)) / upper_arm
    u1 = -2.0 * (2.0 * (static_r - moving_r) - math.sqrt(3.0) * x1 - y1)
    v1 = -4.0 * z1 + k1
    k2 = 2.0 * z1 + (middle - (static_r - moving_r) * (math.sqrt(3.0) * x1 - y1)) / upper_arm
    u2 = -2.0 * (2.0 * (static_r - moving_r) + math.sqrt(3.0) * x1 - y1)
    v2 = -4.0 * z1 + k2
    k3 = z1 + (middle - 2.0 * y1 * (static_r - moving_r)) / 2.0 / upper_arm
    u3 = -2.0 * (static_r - moving_r + y1)
    v3 = -2.0 * z1 + k3

    roots = []
    for k, u, v in ((k1, u1, v1), (k2, u2, v2), (k3, u3, v3)):
        discriminant = u * u - 4.0 * k * v
        if abs(k) < 1e-14 or discriminant < 0.0:
            roots.append(float("nan"))
        else:
            t = (-u - math.sqrt(discriminant)) / (2.0 * k)
            roots.append(math.pi / 2.0 - 2.0 * math.atan(t))
    return np.asarray(roots, dtype=float)


def official_fk(q: np.ndarray, geometry: DeltaGeometry = DeltaGeometry()) -> np.ndarray:
    """Exact project-owned translation of DeltaDisplay::FK_kin.

    This is the raw C++ ``anglesCallback`` convention. The callback first
    calls FK with ``theta_fk`` and then publishes joint.position as
    ``pi/2-theta_fk``. Use :func:`official_fk_joint_state` for the
    ``endCallback`` IK output convention.
    """
    theta1, theta2, theta3 = map(float, np.asarray(q, dtype=float))
    lower_arm, static_r, moving_r, upper_arm = geometry.l, geometry.R, geometry.r, geometry.L
    a1 = math.sqrt(3.0) / 2.0 * (static_r + upper_arm * math.sin(theta1) - moving_r)
    b1 = (static_r + upper_arm * math.sin(theta1) - moving_r) / 2.0
    c1 = upper_arm * math.cos(theta1)
    a2 = -math.sqrt(3.0) / 2.0 * (static_r + upper_arm * math.sin(theta2) - moving_r)
    b2 = (static_r + upper_arm * math.sin(theta2) - moving_r) / 2.0
    c2 = upper_arm * math.cos(theta2)
    b3 = static_r + upper_arm * math.sin(theta3) - moving_r
    c3 = upper_arm * math.cos(theta3)
    d1 = (a1 * a1 + b1 * b1 + c1 * c1 - b3 * b3 - c3 * c3) / 2.0
    d2 = (a2 * a2 + b2 * b2 + c2 * c2 - b3 * b3 - c3 * c3) / 2.0
    b13, c13 = b1 + b3, c1 - c3
    b23, c23 = b2 + b3, c2 - c3
    den = a2 * b13 - a1 * b23
    if abs(den) < 1e-14:
        return np.full(3, np.nan)
    e2 = (a2 * c13 - a1 * c23) / den
    f2 = (a2 * d1 - a1 * d2) / den
    e1 = (b13 * c23 - b23 * c13) / den
    f1 = (b13 * d2 - b23 * d1) / den
    aa = e1 * e1 + e2 * e2 + 1.0
    bb = 2.0 * e2 * f2 + 2.0 * b3 * e2 + 2.0 * e1 * f1 + 2.0 * c3
    cc = f2 * f2 + b3 * b3 + 2.0 * b3 * f2 + f1 * f1 + c3 * c3 - lower_arm * lower_arm
    disc = bb * bb - 4.0 * aa * cc
    if disc < 0.0:
        return np.full(3, np.nan)
    z = (-bb - math.sqrt(disc)) / (2.0 * aa)
    return np.asarray([e1 * z + f1, e2 * z + f2, z], dtype=float)


def official_fk_joint_state(q: np.ndarray, geometry: DeltaGeometry = DeltaGeometry()) -> np.ndarray:
    """FK residual in the joint-state convention emitted by endCallback."""
    return official_fk(math.pi / 2.0 - np.asarray(q, dtype=float), geometry)


def official_joint_points(
    point_a0: np.ndarray, q: np.ndarray, geometry: DeltaGeometry = DeltaGeometry()
) -> dict[str, np.ndarray]:
    """Exact A/B/C/left-right point construction from getJointPoints."""
    x, y, z = map(float, np.asarray(point_a0, dtype=float))
    theta = np.asarray(q, dtype=float)
    R, r, L = geometry.R, geometry.r, geometry.L
    A = np.column_stack((R * np.cos(PHI), R * np.sin(PHI), np.zeros(3)))
    B = np.column_stack(
        (
            R * np.cos(PHI) + L * np.cos(theta) * np.cos(PHI),
            R * np.sin(PHI) + L * np.cos(theta) * np.sin(PHI),
            -L * np.sin(theta),
        )
    )
    C = np.column_stack((r * np.cos(PHI) + x, r * np.sin(PHI) + y, np.full(3, z)))
    half = 0.5 * math.pi / 3.0
    length = 2.0 * r * math.sin(half)
    left, right, c_left, c_right = [], [], [], []
    rotations = [PHI[0] - PHI[2], PHI[1] - PHI[2], 0.0]
    for i, angle in enumerate(rotations):
        rot = np.array(
            [[math.cos(angle), -math.sin(angle), 0.0], [math.sin(angle), math.cos(angle), 0.0], [0.0, 0.0, 1.0]]
        )
        cl = np.array([r * math.cos(PHI[2] - half), r * math.sin(PHI[2] - half), z])
        cr = np.array([r * math.cos(PHI[2] + half), r * math.sin(PHI[2] + half), z])
        cl[:2] += [x, y]
        cr[:2] += [x, y]
        c_left.append(rot @ (cl - np.array([x, y, 0.0])) + np.array([x, y, 0.0]))
        c_right.append(rot @ (cr - np.array([x, y, 0.0])) + np.array([x, y, 0.0]))
        left.append(B[i] + rot @ np.array([-length / 2.0, 0.0, 0.0]))
        right.append(B[i] + rot @ np.array([length / 2.0, 0.0, 0.0]))
    return {
        "A": A,
        "B": B,
        "C": C,
        "B_left": np.asarray(left),
        "B_right": np.asarray(right),
        "C_left": np.asarray(c_left),
        "C_right": np.asarray(c_right),
    }


def joint_margin(q: np.ndarray) -> float:
    q = np.asarray(q, dtype=float)
    return float(np.min(np.minimum(q, math.pi / 2.0 - q)))
