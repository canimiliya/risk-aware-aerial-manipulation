"""Materialize per-round S2-R5 evidence summaries."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "docs/evidence/S2-R5"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    baseline = read(EV / "rounds/round_0/fixed_points.json")
    cumulative = [float(x["joint_margin_rad"]) for x in baseline["fixed_points"]]
    for i in range(4):
        violation = read(EV / "rounds" / f"round_{i}/current_q2_violation.json")
        if i:
            constraints = read(EV / "rounds" / f"round_{i}/constraints.json")
            cumulative.extend(float(x["target_joint_margin_rad"]) for x in constraints["new_mode3"])
            validation = read(EV / "rounds" / f"round_{i}/validation_2000hz.json")
        else:
            validation = {}
        direction = read(EV / "rounds" / f"round_{i}/direction_validation.json")
        summary = {
            "round": i,
            "analysis_sample_hz": violation["sample_hz"],
            "adaptive_dt_s": violation["adaptive_dt_s"],
            "sample_count": violation["sample_count"],
            "baseline_mode3_count": len(baseline["fixed_points"]),
            "new_mode3_count": 0 if i == 0 else len(read(EV / "rounds" / f"round_{i}/constraints.json")["new_mode3"]),
            "cumulative_mode3_count": len(cumulative),
            "q_min_rad": violation["q_min_rad"],
            "q_max_rad": violation["q_max_rad"],
            "q2_min_rad": violation["q_min_rad"][1],
            "violating_intervals": [{"entry_s": x["entry"]["time_s"], "minimum_s": x["minimum"]["time_s"], "exit_s": x["exit"]["time_s"]} for x in violation["violating_intervals"]],
            "fixed_point_margins_rad": cumulative,
            "overshoot_between_fixed_points": bool(not violation["joint_gate_pass"]),
            "joint_gate_pass": validation.get("joint_gate_pass", False) if i else False,
            "full_body_gate_pass": validation.get("full_body_gate_pass", None),
            "min_full_body_clearance_m": validation.get("min_full_body_clearance_m", baseline["static_clearance_gate_m"]),
            "component_min_clearance_m": validation.get("component_min_clearance_m", {}),
            "dangerous_component": validation.get("dangerous_component"),
            "direction_pass": direction["pass"],
            "direction_error_m": direction["direction_error_m"],
            "max_fk_residual_m": validation.get("max_fk_residual_m"),
            "ik_no_solution_count": validation.get("ik_no_solution_count", violation["ik_no_solution_count"]),
            "arm_polynomial_max_curvature_m_s2": validation.get("arm_polynomial_max_curvature_m_s2"),
            "nearest_new_fixed_point_time_s": validation.get("nearest_new_fixed_point_time_s"),
            "nearest_new_fixed_point_cartesian_distance_m": validation.get("nearest_new_fixed_point_cartesian_distance_m"),
            "projection_is_not_output_trajectory": True,
        }
        out = EV / "rounds" / f"round_{i}/round_summary.json"
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
