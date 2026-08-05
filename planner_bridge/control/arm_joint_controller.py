"""PD joint target controller for the three active Delta inputs."""

from __future__ import annotations

import numpy as np

from .contracts import JointCommand


class ArmJointController:
    def __init__(self, config: dict[str, object]) -> None:
        self.kp = np.asarray(config["kp"], dtype=float)
        self.kd = np.asarray(config["kd"], dtype=float)
        self.max_effort = np.asarray(config["max_effort_nm"], dtype=float)
        self.lower = np.asarray(config["lower_rad"], dtype=float)
        self.upper = np.asarray(config["upper_rad"], dtype=float)

    def compute(self, q: np.ndarray, dq: np.ndarray, q_ref: np.ndarray, dq_ref: np.ndarray) -> JointCommand:
        q_ref = np.clip(np.asarray(q_ref, dtype=float), self.lower, self.upper)
        effort_raw = self.kp * (q_ref - q) + self.kd * (np.asarray(dq_ref, dtype=float) - dq)
        effort_clipped = np.clip(effort_raw, -self.max_effort, self.max_effort)
        return JointCommand(q_ref, np.asarray(dq_ref, dtype=float), effort_raw, effort_clipped, np.abs(effort_raw) > self.max_effort + 1e-12)
