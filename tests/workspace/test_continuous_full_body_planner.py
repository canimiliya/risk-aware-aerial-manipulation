from pathlib import Path

import numpy as np
import yaml

from planner_bridge.workspace.continuous_full_body_planner import (
    evaluate_continuous_plan,
    interpolate_waypoints,
    quintic_blend,
)
from planner_bridge.workspace.delta_arm_model import DeltaArmModel
from planner_bridge.workspace.evaluate_task_poses import POSES


ROOT = Path(__file__).resolve().parents[2]


def test_quintic_blend_has_zero_endpoint_slope() -> None:
    assert quintic_blend(0.0) == 0.0
    assert quintic_blend(1.0) == 1.0
    assert abs(quintic_blend(1e-5)) < 1e-12
    assert abs(1.0 - quintic_blend(1.0 - 1e-5)) < 1e-12


def test_interpolation_preserves_p0_p6_and_c2_contract() -> None:
    trajectory = interpolate_waypoints([(name, q) for name, q, _ in POSES], 11)
    assert len(trajectory) == 61
    np.testing.assert_allclose(trajectory[0]["q_rad"], POSES[0][1])
    np.testing.assert_allclose(trajectory[-1]["q_rad"], POSES[-1][1])
    assert trajectory[0]["vehicle_pose_WB"] == [0.0] * 6


def test_nominal_continuous_plan_has_no_invalid_samples() -> None:
    scene = yaml.safe_load((ROOT / "configs/scene/s2_crossarm_nominal.yaml").read_text(encoding="utf-8"))
    trajectory = interpolate_waypoints([(name, q) for name, q, _ in POSES], 21)
    result = evaluate_continuous_plan(DeltaArmModel(), scene, trajectory)
    assert result["invalid_sample_count"] == 0
    assert result["metrics"]["min_clearance_m"] >= 0.010
    assert result["metrics"]["min_joint_margin"] >= 0.10


def test_continuous_metrics_are_finite() -> None:
    scene = yaml.safe_load((ROOT / "configs/scene/s2_crossarm_nominal.yaml").read_text(encoding="utf-8"))
    trajectory = interpolate_waypoints([(name, q) for name, q, _ in POSES], 5)
    result = evaluate_continuous_plan(DeltaArmModel(), scene, trajectory)
    assert all(np.isfinite(float(value)) for value in result["metrics"].values())
