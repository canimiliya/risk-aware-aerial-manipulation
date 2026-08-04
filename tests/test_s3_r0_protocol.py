from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from planner_bridge.execution.official_delta_kinematics import official_fk_joint_state
from planner_bridge.protocol.frames import compose_world_ee, normalize_quaternion_xyzw
from planner_bridge.protocol.load_trajectory import load_bundle
from planner_bridge.protocol.polynomial import sample_message
from planner_bridge.protocol.recorder import PlaybackRecorder
from planner_bridge.protocol.validation import validate_bundle

ROOT = Path(__file__).resolve().parents[1]


def test_nominal_and_repeat_bundles_validate_and_have_full_state() -> None:
    for name in ("nominal_100w0", "nominal_repeat_100w0"):
        bundle = load_bundle(ROOT / "data/trajectories/S3-R0" / name)
        assert bundle["sample_hz"] == 200
        assert not validate_bundle(bundle)
        assert len(bundle["frames"]) > 1000
        assert all(len(frame["q_rad"]) == 3 for frame in bundle["frames"])


def test_raw_polynomial_sampling_is_finite_and_monotonic() -> None:
    payload = json.loads((ROOT / "docs/evidence/S2-R6/runtime/nominal_100w0/trajectory.json").read_text(encoding="utf-8"))
    sampled = sample_message(payload, 137.0)
    assert sampled["time"][0] == 0.0
    assert np.all(np.diff(sampled["time"]) > 0)
    assert np.isfinite(sampled["position"]).all()


def test_fk_and_world_ee_contract() -> None:
    bundle = load_bundle(ROOT / "data/trajectories/S3-R0/nominal_100w0")
    for frame in bundle["frames"][::97]:
        q = np.asarray(frame["q_rad"])
        arm = np.asarray(frame["arm_cartesian_position_m"])
        assert np.linalg.norm(official_fk_joint_state(q) - arm) <= 1e-10
        assert np.allclose(compose_world_ee(np.asarray(frame["base_position_m"]), arm), frame["world_ee_position_m"])


def test_quaternion_and_recorder_are_deterministic(tmp_path: Path) -> None:
    assert np.allclose(normalize_quaternion_xyzw(np.array([0.0, 0.0, 0.0, 2.0])), [0.0, 0.0, 0.0, 1.0])
    recorder = PlaybackRecorder()
    recorder.append({"time": 0.0, "contact": [], "penetration_m": 0.0})
    output = tmp_path / "playback.json"
    recorder.write(output)
    assert json.loads(output.read_text(encoding="utf-8"))["records"][0]["contact"] == []


def test_manifest_hashes_match() -> None:
    root = ROOT / "data/trajectories/S3-R0/nominal_100w0"
    manifest = json.loads((root / "sha256_manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected
