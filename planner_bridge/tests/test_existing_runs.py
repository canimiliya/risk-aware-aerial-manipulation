from __future__ import annotations

import json
from pathlib import Path


def test_four_source_runs_have_successful_capture_and_both_topics() -> None:
    root = Path(__file__).resolve().parents[2] / "docs/evidence/S1-R1/r7r3_r1_runtime"
    runs = ("write_r7r3_r1_gpu_run_02", "grasp_r7r3_r1_gpu_run_02", "lift_r7r3_r1_gpu_run_01", "grasp_r7r3_r1_gpu_run_03")
    for run_id in runs:
        run = root / run_id
        result = json.loads((run / "result_summary.json").read_text(encoding="utf-8"))
        assert result["capture_exit"] == 0
        assert (run / "trajectory.json").is_file()
        assert (run / "trajectory_arm.json").is_file()
        base = json.loads((run / "trajectory.json").read_text(encoding="utf-8"))
        arm = json.loads((run / "trajectory_arm.json").read_text(encoding="utf-8"))
        assert base["statistics"]["nan_count"] == 0
        assert base["statistics"]["inf_count"] == 0
        assert arm["statistics"]["nan_count"] == 0
        assert arm["statistics"]["inf_count"] == 0
