from __future__ import annotations

import math

import numpy as np


class OfficialFlatnessMap:
    """Numerically identical translation of the official FlatnessMap::forward path."""

    def __init__(self, mass: float = 1.0, gravity: float = 9.81, dh: float = 0.05, dv: float = 0.05, cp: float = 0.05, veps: float = 0.05):
        self.mass, self.grav, self.dh, self.dv, self.cp, self.veps = mass, gravity, dh, dv, cp, veps

    def forward(self, vel: np.ndarray, acc: np.ndarray, jerk: np.ndarray, yaw: float, yaw_dot: float) -> tuple[float, np.ndarray, np.ndarray]:
        v0, v1, v2 = map(float, vel)
        a0, a1, a2 = map(float, acc)
        j0, j1, j2 = map(float, jerk)
        cp_term = math.sqrt(v0 * v0 + v1 * v1 + v2 * v2 + self.veps)
        w_term = 1.0 + self.cp * cp_term
        w0, w1, w2 = w_term * v0, w_term * v1, w_term * v2
        dh_over_m = self.dh / self.mass
        zu0, zu1, zu2 = a0 + dh_over_m * w0, a1 + dh_over_m * w1, a2 + dh_over_m * w2 + self.grav
        zu_sqr_norm = zu0 * zu0 + zu1 * zu1 + zu2 * zu2
        zu_norm = math.sqrt(zu_sqr_norm)
        z0, z1, z2 = zu0 / zu_norm, zu1 / zu_norm, zu2 / zu_norm
        ng_den = zu_sqr_norm * zu_norm
        ng00, ng01, ng02 = (zu1 * zu1 + zu2 * zu2) / ng_den, -zu0 * zu1 / ng_den, -zu0 * zu2 / ng_den
        ng11, ng12, ng22 = (zu0 * zu0 + zu2 * zu2) / ng_den, -zu1 * zu2 / ng_den, (zu0 * zu0 + zu1 * zu1) / ng_den
        v_dot_a = v0 * a0 + v1 * a1 + v2 * a2
        dw_term = self.cp * v_dot_a / cp_term
        dw0, dw1, dw2 = w_term * a0 + dw_term * v0, w_term * a1 + dw_term * v1, w_term * a2 + dw_term * v2
        dz_term0, dz_term1, dz_term2 = j0 + dh_over_m * dw0, j1 + dh_over_m * dw1, j2 + dh_over_m * dw2
        dz0 = ng00 * dz_term0 + ng01 * dz_term1 + ng02 * dz_term2
        dz1 = ng01 * dz_term0 + ng11 * dz_term1 + ng12 * dz_term2
        dz2 = ng02 * dz_term0 + ng12 * dz_term1 + ng22 * dz_term2
        f0, f1, f2 = self.mass * a0 + self.dv * w0, self.mass * a1 + self.dv * w1, self.mass * (a2 + self.grav) + self.dv * w2
        thrust = z0 * f0 + z1 * f1 + z2 * f2
        tilt_den = math.sqrt(2.0 * (1.0 + z2))
        tilt0, tilt1, tilt2 = 0.5 * tilt_den, -z1 / tilt_den, z0 / tilt_den
        c_half, s_half = math.cos(0.5 * yaw), math.sin(0.5 * yaw)
        quat = np.array([tilt0 * c_half, tilt1 * c_half + tilt2 * s_half, tilt2 * c_half - tilt1 * s_half, tilt0 * s_half])
        c_yaw, s_yaw = math.cos(yaw), math.sin(yaw)
        omg_den = z2 + 1.0
        omg_term = dz2 / omg_den
        omg = np.array([dz0 * s_yaw - dz1 * c_yaw - (z0 * s_yaw - z1 * c_yaw) * omg_term, dz0 * c_yaw + dz1 * s_yaw - (z0 * c_yaw + z1 * s_yaw) * omg_term, (z1 * dz0 - z0 * dz1) / omg_den + yaw_dot])
        return float(thrust), quat, omg


def quaternion_to_rotation_wxyz(quat: np.ndarray) -> np.ndarray:
    w, x, y, z = map(float, quat)
    return np.array(
        [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    )
