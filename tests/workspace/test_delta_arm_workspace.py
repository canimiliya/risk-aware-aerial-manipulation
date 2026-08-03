from __future__ import annotations

import numpy as np

from planner_bridge.workspace.clearance_geometry import Box, point_box_distance
from planner_bridge.workspace.delta_arm_model import DeltaArmModel
from planner_bridge.workspace.jacobian_metrics import jacobian_metrics
from planner_bridge.workspace.sample_joint_workspace import sample_joint_workspace


def test_official_fk_zero_pose_is_finite() -> None:
    model = DeltaArmModel()
    position = model.fk(np.zeros(3))
    assert np.all(np.isfinite(position))
    assert np.allclose(position, [0.0, 0.0, -0.2502497920131672], atol=1e-12)


def test_fk_boundary_sampling_contains_corners() -> None:
    model = DeltaArmModel()
    qs, positions, valid = sample_joint_workspace(model, count=1000, seed=20260803)
    assert qs.shape == (1000, 3)
    assert positions.shape == (1000, 3)
    assert valid.shape == (1000,)
    assert np.all(np.isfinite(positions[valid]))
    assert any(np.allclose(q, model.joint_lower) for q in qs)
    assert any(np.allclose(q, model.joint_upper) for q in qs)


def test_finite_difference_jacobian_and_joint_margin() -> None:
    model = DeltaArmModel()
    q = np.array([0.0, 0.0, 0.0])
    metrics = jacobian_metrics(model, q)
    assert metrics["min_singular_value"] > 0
    assert metrics["condition_number"] < 10
    assert model.normalized_joint_margin(q) == 0.5


def test_clearance_box_distance() -> None:
    box = Box("test", np.zeros(3), np.ones(3))
    assert point_box_distance(np.array([2.0, 0.5, 0.5]), box) == 1.5
