"""Independent S4-R0 metric and evidence gate."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    summary = json.loads((ROOT / "docs/evidence/S4-R0/summary/s4_r0_metrics.json").read_text(encoding="utf-8"))
    runs = summary["runs"]
    hover = [r for r in runs if r["scenario"] == "hover_hold"]
    offsets = [r for r in runs if r["scenario"] == "initial_offset_recovery"]
    arm = [r for r in runs if r["scenario"] == "arm_motion_hold"]
    assert len(hover) == 3 and len(offsets) == 4 and len(arm) == 3
    for r in hover:
        assert r["position_rmse_m"] <= .05 and r["position_max_error_m"] <= .12
        assert r["attitude_rmse_deg"] <= 3 and r["attitude_max_error_deg"] <= 8
        assert r["final_2s_mean_speed_m_s"] <= .10 and r["final_2s_mean_angular_speed_rad_s"] <= .20
    for r in offsets:
        assert r["position_max_error_m"] <= .12 and r["settling_time_position_s"] is not None and r["settling_time_position_s"] <= 3.0
    for r in arm:
        assert r["position_rmse_m"] <= .07 and r["position_max_error_m"] <= .15
        assert r["attitude_max_error_deg"] <= 10 and r["joint_rmse_rad"] <= .05 and r["ee_fk_rmse_m"] <= .03
        assert r["arm_reaction_nonzero"] and r["joint_saturation_ratio"] < 1.0
    assert summary["gravity_drop_probe"]["z_decreased"] and summary["gravity_drop_probe"]["vertical_velocity_negative"]
    assert summary["control_interface"] == "BODY_WRENCH_PLUS_JOINT_TARGETS"
    assert summary["dynamic_model_mode"] == "BASE_DYNAMIC_ARM_REACTION_SURROGATE_V1"
    print(json.dumps({"pass": True, "hover_runs": len(hover), "offset_runs": len(offsets), "arm_runs": len(arm)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
