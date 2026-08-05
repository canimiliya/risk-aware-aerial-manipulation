from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from planner_bridge.execution.official_delta_kinematics import official_fk_joint_state
from planner_bridge.execution.full_body_proxy import point_to_aabb_distance
from planner_bridge.execution.playback_validator import validate_attitude
from planner_bridge.protocol.frames import compose_world_ee, normalize_quaternion_wxyz, rotation_from_quaternion_wxyz, transform_tool_direction
from planner_bridge.protocol.load_trajectory import load_bundle
from planner_bridge.protocol.polynomial import physics_time_grid, sample_message
from planner_bridge.protocol.recorder import PlaybackRecorder
from planner_bridge.protocol.validation import validate_bundle
from scripts.audit.check_s3_r0_isaaclab_interface import _world_ee_contract_is_complete

ROOT = Path(__file__).resolve().parents[1]
WORLD_EE_CONTRACT = "p_WB_plus_R_WB_(R_BA0_p_A0E_plus_t_BA0)"
LEGACY_WORLD_EE_CONTRACT = "_".join(("base", "position", "plus", "a0", "arm", "position"))


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
        rotation = rotation_from_quaternion_wxyz(np.asarray(frame["base_quaternion_WB_wxyz"]))
        assert np.allclose(compose_world_ee(np.asarray(frame["base_position_m"]), arm, rotation), frame["world_ee_position_m"])
        assert np.allclose(
            transform_tool_direction(rotation, np.asarray(frame["tool_direction_A0"])),
            frame["tool_direction_W"],
        )


def test_scene_contracts_share_complete_world_ee_formula() -> None:
    scene_path = ROOT / "docs/evidence/S3-R0/scene_contract.json"
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    shared_keys = (
        "base_frame",
        "arm_frame",
        "a0_origin",
        "T_B_A0_rotation_translation",
        "world_ee",
        "base_quaternion_order",
        "tool_direction_mapping",
        "playback_mode",
    )

    assert scene["world_ee"] == WORLD_EE_CONTRACT
    assert _world_ee_contract_is_complete(scene)
    assert not _world_ee_contract_is_complete({"world_ee": LEGACY_WORLD_EE_CONTRACT})
    assert LEGACY_WORLD_EE_CONTRACT not in scene_path.read_text(encoding="utf-8")

    for name in ("nominal_100w0", "nominal_repeat_100w0"):
        trajectory_path = ROOT / "data/trajectories/S3-R0" / name / "trajectory.json"
        bundle_contract = load_bundle(trajectory_path.parent)["scene_contract"]
        assert bundle_contract["world_ee"] == WORLD_EE_CONTRACT
        assert all(bundle_contract[key] == scene[key] for key in shared_keys)
        assert LEGACY_WORLD_EE_CONTRACT not in trajectory_path.read_text(encoding="utf-8")


def test_quaternion_and_recorder_are_deterministic(tmp_path: Path) -> None:
    assert np.allclose(normalize_quaternion_wxyz(np.array([2.0, 0.0, 0.0, 0.0])), [1.0, 0.0, 0.0, 0.0])
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


def test_240hz_time_grid_has_single_final_duration_sample() -> None:
    total = load_bundle(ROOT / "data/trajectories/S3-R0/nominal_100w0")["frames"][-1]["time"]
    times = physics_time_grid(total)
    assert len(times) == int(np.ceil(total * 240.0)) + 1
    assert np.all(np.diff(times) > 0.0)
    assert times[-1] == total
    assert np.sum(np.isclose(times, total, atol=0.0, rtol=0.0)) == 1


def test_official_flatness_map_parity_and_exact_aabb_distance() -> None:
    bundle = load_bundle(ROOT / "data/trajectories/S3-R0/nominal_100w0")
    frames = bundle["frames"][::211]
    arrays = {"velocity": np.asarray([f["base_velocity_m_s"] for f in frames]), "acceleration": np.asarray([f["base_acceleration_m_s2"] for f in frames]), "jerk": np.asarray([f["base_jerk_m_s3"] for f in frames]), "yaw": np.zeros(len(frames)), "yaw_dot": np.full(len(frames), 0.01)}
    summary, attitude = validate_attitude(arrays)
    assert summary["finite"] is True
    assert summary["quaternion_norm_error_max"] <= 1e-12
    assert np.allclose(attitude["quaternion"], np.asarray([f["base_quaternion_WB_wxyz"] for f in frames]), atol=1e-12)
    assert point_to_aabb_distance(np.asarray([2.0, 0.0, 0.0]), np.zeros(3), np.ones(3)) == 1.5
    assert point_to_aabb_distance(np.asarray([0.0, 0.0, 0.0]), np.zeros(3), np.ones(3)) == 0.0
