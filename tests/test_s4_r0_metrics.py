import json
from pathlib import Path


def test_authoritative_metrics_pass():
    root = Path(__file__).parents[1]
    payload = json.loads((root / "docs/evidence/S4-R0/summary/s4_r0_metrics.json").read_text(encoding="utf-8"))
    assert payload["run_count"] == 11
    assert payload["gravity_drop_probe"]["z_decreased"]
    assert payload["gravity_drop_probe"]["vertical_velocity_negative"]
    hover = [r for r in payload["runs"] if r["scenario"] == "hover_hold"]
    arm = [r for r in payload["runs"] if r["scenario"] == "arm_motion_hold"]
    assert all(r["position_rmse_m"] <= .05 and r["final_2s_mean_speed_m_s"] <= .1 for r in hover)
    assert all(r["joint_rmse_rad"] <= .05 and r["ee_fk_rmse_m"] <= .03 and r["arm_reaction_nonzero"] for r in arm)
