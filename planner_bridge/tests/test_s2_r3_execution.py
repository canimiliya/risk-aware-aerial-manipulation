from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from planner_bridge.execution.official_delta_kinematics import official_fk_joint_state, official_ik
from planner_bridge.execution.playback_validator import evaluate_message, validate_kinematics


ROOT = Path(__file__).resolve().parents[2]


def test_official_ik_fk_random_valid_points_and_boundaries() -> None:
    rng = np.random.default_rng(20260803)
    q_values = rng.uniform(0.02, np.pi / 2.0 - 0.02, size=(1000, 3))
    q_values = np.vstack([q_values, np.asarray([[a, b, c] for a in (0.0, np.pi / 2.0) for b in (0.0, np.pi / 2.0) for c in (0.0, np.pi / 2.0)])])
    points = np.asarray([official_fk_joint_state(q) for q in q_values])
    recovered = np.asarray([official_ik(point) for point in points])
    recovered_points = np.asarray([official_fk_joint_state(q) for q in recovered])
    assert np.isfinite(recovered).all()
    assert np.max(np.linalg.norm(recovered_points - points, axis=1)) < 1e-10
    assert np.max(np.abs(recovered - q_values)) < 1e-9


def test_s2_r2_five_trajectory_groups_have_100_point_ik_loops() -> None:
    variants = ["smoke_free", "loose", "nominal", "nominal_repeat", "narrow"]
    for variant in variants:
        path = ROOT / "data" / "trajectories" / "S2-R2" / "100Hz" / variant / "raw_trajectory_arm.json"
        message = json.loads(path.read_text(encoding="utf-8"))["message"]
        total = float(np.sum(message["time"]))
        times = np.linspace(0.0, total, 100)
        arm = evaluate_message(message, times, arm=True)
        result, _ = validate_kinematics({**arm, "time": times})
        assert result["samples"] == 100
        assert result["ik_no_solution_count"] == 0
        assert result["fk_residual_max_m"] < 1e-9
        assert np.isfinite(result["min_joint_margin_rad"])
