import math

import numpy as np

from planner_bridge.constraints.detect_joint_branch_violation import detect_violations
from planner_bridge.constraints.generate_adaptive_mode3_constraints import build_mode3_row, generate_constraints
from planner_bridge.constraints.project_arm_point_to_envelope import project_joint_state


ROOT = __import__("pathlib").Path(__file__).resolve().parents[3]


def test_project_joint_state_respects_task_contract():
    q = project_joint_state(np.array([-0.1, -0.2, 2.0]))
    assert np.all(q >= [0.02, 0.05, 0.02])
    assert np.all(q <= math.pi / 2.0 - 0.02)


def test_mode3_row_uses_official_payload_shape():
    projected = {
        "base_point_WB_m": [1.0, 2.0, 1.5],
        "arm_point_A0_m": [0.0, 0.0, -0.07],
    }
    row = build_mode3_row(projected)
    assert len(row) == 20
    assert row[0] == 3.0
    assert row[1:7] == projected["base_point_WB_m"] + projected["arm_point_A0_m"]
    assert row[7:] == [0.0] * 13


def test_real_r4_detector_finds_two_nominal_q2_intervals():
    arm = ROOT / "docs/evidence/S2-R4/runtime/nominal_run_01/trajectory_arm.json"
    base = ROOT / "docs/evidence/S2-R4/runtime/nominal_run_01/trajectory.json"
    result = detect_violations(arm, base)
    assert len(result["violating_intervals"]) == 2
    assert result["ik_no_solution_count"] == 0
    assert result["joint_gate_pass"] is False
    assert result["q_min_rad"][1] < 0.0


def test_constraints_are_three_per_selected_interval():
    source = ROOT / "docs/evidence/S2-R4/root_cause/current_r4_q2_violation.json"
    violation = __import__("json").loads(source.read_text(encoding="utf-8"))
    rows = generate_constraints(violation, max_intervals=1)
    assert len(rows) == 3
    assert all(item["projection_is_not_output_trajectory"] for item in rows)
    assert all(item["target_q_rad"][1] >= 0.05 for item in rows)
