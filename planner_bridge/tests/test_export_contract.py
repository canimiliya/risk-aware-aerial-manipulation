from __future__ import annotations

import json
from pathlib import Path

from planner_bridge.validation.validate_exported_trajectory import validate_directory


def test_all_four_official_exports_pass() -> None:
    root = Path(__file__).resolve().parents[2] / "data/trajectories/S1-R2"
    directories = [root / name for name in ("write_official", "grasp_official", "lift_official", "grasp_repeat")]
    assert all(validate_directory(directory)["status"] == "PASS" for directory in directories)


def test_contract_metadata_has_no_fake_semantics() -> None:
    metadata = json.loads((Path(__file__).resolve().parents[2] / "data/trajectories/S1-R2/grasp_official/metadata.json").read_text(encoding="utf-8"))
    assert metadata["message_type"] == "quadrotor_msgs/PolynomialTrajectory"
    assert metadata["coordinate_frame"] == "world"
    assert "not encoded" in metadata["units"]["position"]
    assert metadata["segment_count"] == 4
