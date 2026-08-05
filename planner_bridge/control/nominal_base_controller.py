"""Interpretable cascaded PD controller for the S4-R0 base rigid body."""

from __future__ import annotations

import numpy as np

from .contracts import WrenchCommand, clamp_norm, rotation_error_vector


class NominalBaseController:
    """Position/attitude PD controller with explicit, logged saturation."""

    def __init__(self, config: dict[str, object]) -> None:
        self.mass_kg = float(config["mass_kg"])
        self.gravity_m_s2 = float(config["gravity_m_s2"])
        self.kp_pos = np.asarray(config["kp_pos"], dtype=float)
        self.kd_pos = np.asarray(config["kd_pos"], dtype=float)
        self.kp_att = np.asarray(config["kp_att"], dtype=float)
        self.kd_att = np.asarray(config["kd_att"], dtype=float)
        self.inertia_kg_m2 = np.asarray(config["inertia_kg_m2"], dtype=float)
        self.max_force_n = float(config["max_force_n"])
        self.max_torque_nm = np.asarray(config["max_torque_nm"], dtype=float)

    def compute(
        self,
        position: np.ndarray,
        velocity: np.ndarray,
        rotation: np.ndarray,
        angular_velocity_body: np.ndarray,
        reference_position: np.ndarray,
        reference_velocity: np.ndarray | None = None,
        reference_acceleration: np.ndarray | None = None,
        reference_rotation: np.ndarray | None = None,
        reference_angular_velocity: np.ndarray | None = None,
    ) -> WrenchCommand:
        reference_velocity = np.zeros(3) if reference_velocity is None else np.asarray(reference_velocity, dtype=float)
        reference_acceleration = np.zeros(3) if reference_acceleration is None else np.asarray(reference_acceleration, dtype=float)
        reference_rotation = np.eye(3) if reference_rotation is None else np.asarray(reference_rotation, dtype=float)
        reference_angular_velocity = np.zeros(3) if reference_angular_velocity is None else np.asarray(reference_angular_velocity, dtype=float)
        e_p = np.asarray(reference_position, dtype=float) - np.asarray(position, dtype=float)
        e_v = reference_velocity - np.asarray(velocity, dtype=float)
        acceleration_command = reference_acceleration + self.kp_pos * e_p + self.kd_pos * e_v + np.array([0.0, 0.0, self.gravity_m_s2])
        raw_force = self.mass_kg * acceleration_command
        clipped_force, force_saturated = clamp_norm(raw_force, self.max_force_n)
        e_r = rotation_error_vector(reference_rotation, rotation)
        e_omega = np.asarray(angular_velocity_body, dtype=float) - reference_angular_velocity
        # rotation_error_vector is defined as cross(actual_axis, reference_axis),
        # hence its sign is opposite to the corrective body torque.
        raw_torque = self.kp_att * e_r - self.kd_att * e_omega + np.cross(angular_velocity_body, self.inertia_kg_m2 * angular_velocity_body)
        clipped_torque = np.clip(raw_torque, -self.max_torque_nm, self.max_torque_nm)
        torque_saturated = bool(np.any(np.abs(raw_torque) > self.max_torque_nm + 1e-12))
        return WrenchCommand(raw_force, clipped_force, raw_torque, clipped_torque, force_saturated, torque_saturated)
