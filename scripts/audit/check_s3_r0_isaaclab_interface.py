from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FIXED_OLD_HEAD = "ccf90caa4ea9a0c826efadadb667cf42a54c9a15"
S3_BRANCH = "agent/s3-r0-isaaclab-trajectory-interface"
WORLD_EE_CONTRACT = "p_WB_plus_R_WB_(R_BA0_p_A0E_plus_t_BA0)"
sys.path.insert(0, str(ROOT))

from scripts.audit.check_s3_s2_baseline import run as run_baseline
from planner_bridge.protocol.load_trajectory import load_bundle
from planner_bridge.protocol.validation import validate_bundle
from planner_bridge.protocol.frames import rotation_from_quaternion_wxyz
from scripts.s3_r0_gui_visual_capture import (
    CAPTURE_MODE,
    DANGEROUS_FRAME,
    DANGEROUS_FRAME_TOLERANCE,
    DANGEROUS_TIME_S,
    DANGEROUS_TIME_TOLERANCE_S,
    FINAL_FRAME,
    FINAL_TIME_S,
)
from scripts.s3_r0_visual_video_manifest import MIN_VIDEO_FRAMES, VISUAL_CONTRACT_VERSION, inspect_gif


def _git(*args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30.0,
            check=False,
        )
        return completed.stdout.strip()
    except Exception:
        return ""


def _progress_contract(path: Path) -> bool:
    if not path.is_file():
        return False
    required = {"PROCESS_STARTED", "SIMULATION_APP_CREATED", "STAGE_CREATED", "PHYSICS_SCENE_CREATED", "ROBOT_REFERENCE_ADDED", "ROBOT_ASSET_READY", "CROSSARM_SCENE_READY", "ACTIVE_JOINTS_READY", "SIMULATION_CONTEXT_READY", "TIMELINE_PLAYING", "STEP_0", "STEP_N", "STATE_LOG_FLUSHED", "RESULT_WRITTEN", "APP_CLOSED"}
    try:
        events = {json.loads(line).get("event") for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
    except Exception:
        return False
    return required.issubset(events)


def _formal_playback_ok(payload: dict[str, object]) -> bool:
    return bool(
        payload
        and payload.get("frames") == 1255
        and payload.get("expected_physics_steps") == 1255
        and payload.get("actual_physics_steps") == 1255
        and payload.get("complete_duration") is True
        and payload.get("time_alignment_pass") is True
        and payload.get("finite") is True
        and payload.get("monotonic_time") is True
        and payload.get("contact_query") == "PASS"
        and payload.get("exact_clearance_gate") is True
        and float(payload.get("max_arm_fk_error_m", float("inf"))) <= 1e-5
        and float(payload.get("max_world_ee_error_m", float("inf"))) <= 1e-4
        and payload.get("app_closed") is True
        and payload.get("scene_output_created") is True
    )


def _world_ee_contract_is_complete(contract: dict[str, object]) -> bool:
    return contract.get("world_ee") == WORLD_EE_CONTRACT


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_kind(source_run: object) -> str | None:
    name = str(source_run).lower()
    if "repeat" in name:
        return "repeat"
    if "nominal" in name:
        return "nominal"
    return None


def _evidence_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else root / path


def _entry_frame_time(entry: dict[str, object]) -> tuple[int, float] | None:
    frame = entry.get("frame")
    time_s = entry.get("time_s")
    if isinstance(frame, bool) or not isinstance(frame, (int, float)) or int(frame) != frame:
        return None
    if isinstance(time_s, bool) or not isinstance(time_s, (int, float)) or not math.isfinite(float(time_s)):
        return None
    return int(frame), float(time_s)


def _strictly_increasing(values: list[int] | list[float]) -> bool:
    return bool(values) and all(left < right for left, right in zip(values, values[1:]))


def _dangerous_frame_time(frame: int, time_s: float) -> bool:
    return (
        abs(frame - DANGEROUS_FRAME) <= DANGEROUS_FRAME_TOLERANCE
        and abs(time_s - DANGEROUS_TIME_S) <= DANGEROUS_TIME_TOLERANCE_S
    )


def _final_frame_time(frame: int, time_s: float) -> bool:
    return frame == FINAL_FRAME and abs(time_s - FINAL_TIME_S) <= 1e-12


def validate_visual_manifest(root: Path, manifest: dict[str, object]) -> dict[str, object]:
    """Independently validate R8 PNG and chronological local-video evidence."""

    png_issues: list[str] = []
    video_issues: list[str] = []
    png_coverage = {
        "nominal": {"start": False, "dangerous": False, "final": False},
        "repeat": {"start": False, "dangerous": False, "final": False},
    }
    video_coverage = {"nominal": False, "repeat": False}

    png_entries = manifest.get("png")
    if not isinstance(png_entries, list):
        png_issues.append("png_not_a_list")
        png_entries = []
    if manifest.get("png_count") != len(png_entries):
        png_issues.append("png_count_mismatch")
    if len(png_entries) < 12:
        png_issues.append("png_count_below_12")

    for index, raw_entry in enumerate(png_entries):
        prefix = f"png[{index}]"
        if not isinstance(raw_entry, dict):
            png_issues.append(f"{prefix}:not_an_object")
            continue
        entry = raw_entry
        required = ("local_path", "source_run", "frame", "time_s", "view", "sha256", "bytes")
        for field in required:
            if field not in entry:
                png_issues.append(f"{prefix}:missing_{field}")
        if entry.get("committed", True) is not True:
            png_issues.append(f"{prefix}:png_must_be_committed")
        path = _evidence_path(root, entry.get("local_path"))
        if path is None or not path.is_file():
            png_issues.append(f"{prefix}:file_missing")
        else:
            actual_bytes = path.stat().st_size
            if actual_bytes <= 0:
                png_issues.append(f"{prefix}:file_empty")
            if entry.get("bytes") != actual_bytes:
                png_issues.append(f"{prefix}:bytes_mismatch")
            if entry.get("sha256") != _sha256(path):
                png_issues.append(f"{prefix}:sha256_mismatch")

        kind = _run_kind(entry.get("source_run"))
        frame_time = _entry_frame_time(entry)
        if kind is None:
            png_issues.append(f"{prefix}:unknown_source_run")
            continue
        if frame_time is None:
            png_issues.append(f"{prefix}:invalid_frame_time")
            continue
        frame, time_s = frame_time
        is_r8_entry = entry.get("capture_role") is not None or entry.get("capture_mode") is not None
        if is_r8_entry and entry.get("capture_mode") != CAPTURE_MODE:
            png_issues.append(f"{prefix}:invalid_capture_mode")
        if frame == 0 and abs(time_s) <= 1e-12 and entry.get("capture_mode") == CAPTURE_MODE:
            png_coverage[kind]["start"] = True
        if _dangerous_frame_time(frame, time_s) and entry.get("capture_mode") == CAPTURE_MODE:
            png_coverage[kind]["dangerous"] = True
        if _final_frame_time(frame, time_s):
            png_coverage[kind]["final"] = True

    for kind, phases in png_coverage.items():
        for phase, covered in phases.items():
            if not covered:
                png_issues.append(f"{kind}_{phase}_png_missing")

    video_entries = manifest.get("video")
    if not isinstance(video_entries, list):
        video_issues.append("video_not_a_list")
        video_entries = []
    if manifest.get("video_count") != len(video_entries):
        video_issues.append("video_count_mismatch")
    if len(video_entries) < 2:
        video_issues.append("video_count_below_2")

    required_video_fields = (
        "local_path",
        "sha256",
        "bytes",
        "duration_s",
        "fps",
        "width",
        "height",
        "source_run",
        "frame_count",
        "source_frames",
        "source_times_s",
        "time_start_s",
        "time_end_s",
        "camera_view",
        "chronological",
        "covers_start",
        "covers_dangerous_time",
        "covers_final",
        "created_at",
        "format",
        "committed",
    )
    for index, raw_entry in enumerate(video_entries):
        prefix = f"video[{index}]"
        if not isinstance(raw_entry, dict):
            video_issues.append(f"{prefix}:not_an_object")
            continue
        entry = raw_entry
        for field in required_video_fields:
            if field not in entry:
                video_issues.append(f"{prefix}:missing_{field}")

        kind = _run_kind(entry.get("source_run"))
        if kind is None:
            video_issues.append(f"{prefix}:unknown_source_run")
        if entry.get("committed") is not False:
            video_issues.append(f"{prefix}:video_must_be_local_only")
        if entry.get("format") != "GIF":
            video_issues.append(f"{prefix}:unsupported_format")
        if entry.get("visual_contract_version") != VISUAL_CONTRACT_VERSION:
            video_issues.append(f"{prefix}:wrong_visual_contract_version")
        if not isinstance(entry.get("camera_view"), str) or not entry.get("camera_view"):
            video_issues.append(f"{prefix}:camera_view_missing")

        frames = entry.get("source_frames")
        times = entry.get("source_times_s")
        frame_count = entry.get("frame_count")
        valid_frames = isinstance(frames, list) and all(
            not isinstance(value, bool) and isinstance(value, (int, float)) and int(value) == value for value in frames
        )
        valid_times = isinstance(times, list) and all(
            not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value)) for value in times
        )
        if not valid_frames or not valid_times:
            video_issues.append(f"{prefix}:invalid_source_timeline")
            parsed_frames: list[int] = []
            parsed_times: list[float] = []
        else:
            parsed_frames = [int(value) for value in frames]
            parsed_times = [float(value) for value in times]
        if (
            isinstance(frame_count, bool)
            or not isinstance(frame_count, int)
            or frame_count < MIN_VIDEO_FRAMES
            or frame_count != len(parsed_frames)
            or frame_count != len(parsed_times)
        ):
            video_issues.append(f"{prefix}:frame_count_contract")
        chronological = _strictly_increasing(parsed_frames) and _strictly_increasing(parsed_times)
        covers_start = bool(parsed_frames and parsed_frames[0] == 0 and abs(parsed_times[0]) <= 1e-12)
        covers_dangerous = any(
            _dangerous_frame_time(frame, time_s) for frame, time_s in zip(parsed_frames, parsed_times)
        )
        covers_final = bool(parsed_frames and _final_frame_time(parsed_frames[-1], parsed_times[-1]))
        recomputed_flags = {
            "chronological": chronological,
            "covers_start": covers_start,
            "covers_dangerous_time": covers_dangerous,
            "covers_final": covers_final,
        }
        for field, recomputed in recomputed_flags.items():
            if entry.get(field) is not True or not recomputed:
                video_issues.append(f"{prefix}:{field}_failed")
        if parsed_times:
            if not isinstance(entry.get("time_start_s"), (int, float)) or abs(float(entry["time_start_s"]) - parsed_times[0]) > 1e-12:
                video_issues.append(f"{prefix}:time_start_mismatch")
            if not isinstance(entry.get("time_end_s"), (int, float)) or abs(float(entry["time_end_s"]) - parsed_times[-1]) > 1e-12:
                video_issues.append(f"{prefix}:time_end_mismatch")

        source_image_hashes = entry.get("source_image_sha256")
        source_state_hashes = entry.get("source_state_sha256")
        valid_source_image_hashes = bool(
            isinstance(source_image_hashes, list)
            and all(isinstance(value, str) and value for value in source_image_hashes)
        )
        valid_source_state_hashes = bool(
            isinstance(source_state_hashes, list)
            and all(isinstance(value, str) and value for value in source_state_hashes)
        )
        if (
            not valid_source_image_hashes
            or len(source_image_hashes) != len(parsed_frames)
            or len(set(source_image_hashes)) < 2
        ):
            video_issues.append(f"{prefix}:source_images_do_not_prove_motion")
        if (
            not valid_source_state_hashes
            or len(source_state_hashes) != len(parsed_frames)
            or len(set(source_state_hashes)) < 2
        ):
            video_issues.append(f"{prefix}:source_states_do_not_prove_motion")
        if entry.get("motion_detected") is not True:
            video_issues.append(f"{prefix}:motion_not_detected")
        if not isinstance(entry.get("created_at"), str) or not entry.get("created_at"):
            video_issues.append(f"{prefix}:created_at_missing")

        path = _evidence_path(root, entry.get("local_path"))
        physical: dict[str, object] | None = None
        if path is None or not path.is_file():
            video_issues.append(f"{prefix}:file_missing")
        else:
            actual_bytes = path.stat().st_size
            if actual_bytes <= 0:
                video_issues.append(f"{prefix}:file_empty")
            if entry.get("bytes") != actual_bytes:
                video_issues.append(f"{prefix}:bytes_mismatch")
            if entry.get("sha256") != _sha256(path):
                video_issues.append(f"{prefix}:sha256_mismatch")
            try:
                physical = inspect_gif(path)
            except Exception:
                video_issues.append(f"{prefix}:gif_decode_failed")
        if physical is not None:
            for field in ("width", "height", "frame_count"):
                if entry.get(field) != physical[field]:
                    video_issues.append(f"{prefix}:{field}_mismatch")
            duration_tolerance = max(1e-9, 0.001 * int(physical["frame_count"]))
            if not isinstance(entry.get("duration_s"), (int, float)) or abs(float(entry["duration_s"]) - float(physical["duration_s"])) > duration_tolerance:
                video_issues.append(f"{prefix}:duration_mismatch")
            if not isinstance(entry.get("fps"), (int, float)) or abs(float(entry["fps"]) - float(physical["fps"])) > 1e-9:
                video_issues.append(f"{prefix}:fps_mismatch")
            if int(physical["distinct_frame_count"]) < 2:
                video_issues.append(f"{prefix}:gif_frames_not_visually_distinct")

        if kind is not None and all(recomputed_flags.values()):
            video_coverage[kind] = True

    for kind, covered in video_coverage.items():
        if not covered:
            video_issues.append(f"{kind}_chronological_video_missing")

    png_ok = not png_issues
    video_ok = not video_issues
    manifest_ok = bool(
        manifest.get("decision") == "PASS"
        and manifest.get("visual_contract_version") == VISUAL_CONTRACT_VERSION
        and png_ok
        and video_ok
    )
    return {
        "png_ok": png_ok,
        "video_ok": video_ok,
        "manifest_ok": manifest_ok,
        "png_issues": png_issues,
        "video_issues": video_issues,
        "png_coverage": png_coverage,
        "video_coverage": video_coverage,
    }


def run(root: Path = ROOT) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}

    def check(name: str, value: bool, hard: bool = True) -> None:
        checks[name] = value
        if not value:
            (errors if hard else warnings).append(name)

    playback_script = (root / "scripts/s3_r0_reference_playback.py").read_text(encoding="utf-8")
    formal_loop_start = playback_script.find("for index, reference_time in enumerate(target_times):")
    formal_loop_end = playback_script.find('"PHYSICS_LOOP_COMPLETE"', formal_loop_start)
    formal_loop = playback_script[formal_loop_start:formal_loop_end] if formal_loop_start >= 0 and formal_loop_end > formal_loop_start else ""
    remote_head = _git("ls-remote", "origin", f"refs/heads/{S3_BRANCH}").split("\t", 1)[0]
    check("remote_correction_head", bool(remote_head) and remote_head != FIXED_OLD_HEAD)
    check("playback_physics_context_contract", "SimulationContext" in playback_script and "sim.step(render=render_now)" in formal_loop and "app.update()" not in formal_loop)
    check("playback_diagnostics_contract", all(flag in playback_script for flag in ("--smoke-steps", "--max-runtime-s", "--heartbeat-every", "--checkpoint-every", "--headless", "--render-every", "--progress-output", "--state-output", "--result-output", "os.replace")))

    baseline = run_baseline(root)
    check("authoritative_s2_baseline", baseline["decision"] == "PASS")
    bundle_scene_contracts = []
    for variant in ("nominal_100w0", "nominal_repeat_100w0"):
        bundle = load_bundle(root / "data/trajectories/S3-R0" / variant)
        check(f"{variant}_protocol", not validate_bundle(bundle))
        check(f"{variant}_raw_polynomials", all((root / "data/trajectories/S3-R0" / variant / name).is_file() for name in ("raw_base_polynomial.json", "raw_arm_polynomial.json")))
        frames = bundle["frames"]
        check(f"{variant}_dynamic_attitude", any(np.linalg.norm(frame["base_body_omega_B_rad_s"]) > 1e-12 for frame in frames))
        check(f"{variant}_quaternion_wxyz", all(abs(np.linalg.norm(frame["base_quaternion_WB_wxyz"]) - 1.0) <= 1e-12 for frame in frames))
        check(f"{variant}_rotation_contract", all(np.linalg.norm(rotation_from_quaternion_wxyz(frame["base_quaternion_WB_wxyz"]).T @ rotation_from_quaternion_wxyz(frame["base_quaternion_WB_wxyz"]) - np.eye(3)) <= 1e-10 for frame in frames))
        bundle_scene_contract = bundle.get("scene_contract", {})
        bundle_scene_contracts.append(bundle_scene_contract)
        check(f"{variant}_world_ee_b_to_a0_contract", _world_ee_contract_is_complete(bundle_scene_contract))
    scene = json.loads((root / "docs/evidence/S3-R0/scene_contract.json").read_text(encoding="utf-8"))
    check("scene_contract_playback_mode", scene.get("playback_mode") == "REFERENCE_STATE_PLAYBACK")
    check("scene_contract_world_ee_b_to_a0_contract", _world_ee_contract_is_complete(scene))
    shared_scene_keys = (
        "base_frame",
        "arm_frame",
        "a0_origin",
        "T_B_A0_rotation_translation",
        "world_ee",
        "base_quaternion_order",
        "tool_direction_mapping",
        "playback_mode",
    )
    check(
        "scene_contract_bundle_consistency",
        all(all(bundle_contract.get(key) == scene.get(key) for key in shared_scene_keys) for bundle_contract in bundle_scene_contracts),
    )
    check(
        "scene_contract",
        checks["scene_contract_playback_mode"]
        and checks["scene_contract_world_ee_b_to_a0_contract"]
        and checks["scene_contract_bundle_consistency"],
    )
    gate_path = root / "docs/evidence/S3-R0/environment/environment_gate.json"
    if gate_path.is_file():
        environment = json.loads(gate_path.read_text(encoding="utf-8"))
        check("python_311_environment", environment.get("python", "").startswith("3.11"))
        check("isaaclab_import", bool(environment.get("isaaclab_import")), hard=False)
        check("isaacsim_import", bool(environment.get("isaacsim_import")), hard=False)
        check("physx_smoke", bool(environment.get("physx_smoke")), hard=False)
    else:
        env = root / "docs/evidence/S3-R0/environment_install_attempt.json"
        environment = json.loads(env.read_text(encoding="utf-8"))
        check("python_311_environment", environment.get("python", "").startswith("3.11"))
        check("isaaclab_import", importlib.util.find_spec("isaaclab") is not None, hard=False)
        check("isaacsim_import", importlib.util.find_spec("isaacsim") is not None, hard=False)
        check("physx_smoke", environment.get("physx_smoke") == "PASS", hard=False)
    api_probe_path = root / "docs/evidence/S3-R0/physics_scene_api_probe.json"
    api_probe = json.loads(api_probe_path.read_text(encoding="utf-8")) if api_probe_path.is_file() else {}
    check(
        "physics_scene_api_probe",
        api_probe.get("decision") == "PASS"
        and api_probe.get("usdphysics_scene_has_timestep_creator") is False
        and api_probe.get("physx_scene_api_has_timestep_creator") is True
        and api_probe.get("physics_dt_s") == 1.0 / 240.0,
    )
    playback_path = root / "docs/evidence/S3-R0/isaac_playback_nominal_1_r5_grid.json"
    playback = json.loads(playback_path.read_text(encoding="utf-8")) if playback_path.is_file() else {}
    distance_summary_path = root / "docs/evidence/S3-R0/distance_representation/formal_distance_summary.json"
    distance_summary = json.loads(distance_summary_path.read_text(encoding="utf-8")) if distance_summary_path.is_file() else {}
    smoke_path = root / "docs/evidence/S3-R0/isaac_playback_smoke64_r7_corrected_dp2.json"
    smoke = json.loads(smoke_path.read_text(encoding="utf-8")) if smoke_path.is_file() else {}
    readback_path = root / "docs/evidence/S3-R0/distance_representation/isaac_scene_aabb_readback.json"
    readback = json.loads(readback_path.read_text(encoding="utf-8")) if readback_path.is_file() else {}
    check("canonical_240hz_sample_count", bool(playback) and playback.get("canonical_240hz_sample_count") == int(np.ceil(float(playback.get("duration_s", 0.0)) * 240.0)) + 1)
    check("smoke_64_steps", smoke.get("expected_physics_steps") == 64 and smoke.get("actual_physics_steps") == 64 and smoke.get("app_closed") is True and smoke.get("decision") == "SMOKE_64_STEP_PASS")
    check("smoke_heartbeat_checkpoints", _progress_contract(root / "docs/evidence/S3-R0/isaac_playback_smoke64_r7_corrected_dp2.progress.jsonl"))
    check(
        "isaac_scene_aabb_readback",
        readback.get("decision") == "PASS"
        and readback.get("overall_pass") is True
        and all(row.get("pass") is True for row in readback.get("boxes", {}).values())
        and readback.get("column_readback_z_bounds_m") == [0.07999999999999996, 1.38],
    )
    if playback:
        check("playback_runs", playback.get("frames", 0) > 0 and playback.get("finite") is True and playback.get("monotonic_time") is True and playback.get("app_closed") is True)
        check("expected_actual_physics_steps", playback.get("expected_physics_steps") == playback.get("actual_physics_steps"))
        check("time_alignment", playback.get("max_time_alignment_error_s", float("inf")) <= 1e-9 and playback.get("time_alignment_pass") is True)
        check("complete_duration", playback.get("complete_duration") is True)
        check("joint_mapping_error", playback.get("max_joint_state_write_readback_error_rad", float("inf")) <= 1e-5)
        check("arm_fk_error", playback.get("max_arm_fk_error_m", float("inf")) <= 1e-5)
        check("world_ee_error", playback.get("max_world_ee_error_m", float("inf")) <= 1e-4)
        check("playback_heartbeat_checkpoints", _progress_contract(root / "docs/evidence/S3-R0/isaac_playback_nominal_1_r5_grid.progress.jsonl"))
        check("contact_query", playback.get("contact_query") == "PASS")
        check("exact_sampled_proxy_clearance", playback.get("clearance_metric") == "EXACT_FOR_FROZEN_S2_SAMPLED_PROXY_NOT_MESH_EXACT" and playback.get("exact_clearance_gate") is True)
        check("isaac_aabb_clearance_gate", distance_summary.get("contracts", {}).get("isaac_aabb_clearance_gate") is True)
        check("state_replay_s2_clearance_delta", distance_summary.get("contracts", {}).get("state_replay_s2_clearance_delta") is True)
        check("s2_points_contained_by_isaac_aabbs", distance_summary.get("contracts", {}).get("s2_points_contained_by_isaac_aabbs") is True)
        check("framewise_conservative_order", distance_summary.get("contracts", {}).get("framewise_conservative_order") is True)
        check("geometry_representation_delta_reported", distance_summary.get("contracts", {}).get("geometry_representation_delta_reported") is True)
    else:
        for name in ("playback_runs", "expected_actual_physics_steps", "time_alignment", "complete_duration", "exact_sampled_proxy_clearance", "isaac_aabb_clearance_gate", "state_replay_s2_clearance_delta", "s2_points_contained_by_isaac_aabbs", "framewise_conservative_order"):
            check(name, False)
    required_runs = {
        "nominal_x3": [
            root / "docs/evidence/S3-R0/isaac_playback_nominal_1_r5_grid.json",
            root / "docs/evidence/S3-R0/isaac_playback_nominal_2_r5.json",
            root / "docs/evidence/S3-R0/isaac_playback_nominal_3_r5.json",
        ],
        "nominal_repeat": [root / "docs/evidence/S3-R0/isaac_playback_nominal_repeat_r5.json"],
        "nominal_gui": [root / "docs/evidence/S3-R0/isaac_playback_nominal_gui_r7_corrected_dp.json"],
        "repeat_gui": [root / "docs/evidence/S3-R0/isaac_playback_nominal_repeat_gui_r7_corrected_dp.json"],
    }
    for name, paths in required_runs.items():
        check(name, all(path.is_file() for path in paths), hard=name in {"nominal_x3", "nominal_repeat", "nominal_gui", "repeat_gui"})
    nominal_gui_path = required_runs["nominal_gui"][0]
    repeat_gui_path = required_runs["repeat_gui"][0]
    nominal_gui = json.loads(nominal_gui_path.read_text(encoding="utf-8")) if nominal_gui_path.is_file() else {}
    repeat_gui = json.loads(repeat_gui_path.read_text(encoding="utf-8")) if repeat_gui_path.is_file() else {}
    check("nominal_gui_contract", _formal_playback_ok(nominal_gui))
    check("repeat_gui_contract", _formal_playback_ok(repeat_gui))
    visuals = root / "docs/evidence/S3-R0/visuals/manifest.json"
    visual_manifest = json.loads(visuals.read_text(encoding="utf-8")) if visuals.is_file() else {}
    visual_contract = validate_visual_manifest(root, visual_manifest)
    check("visual_png_contract", visual_contract["png_ok"] is True)
    check("visual_video_contract", visual_contract["video_ok"] is True)
    check("visual_manifest", visual_contract["manifest_ok"] is True)
    if not distance_summary.get("contracts", {}).get("s2_points_contained_by_isaac_aabbs", False):
        errors.append("geometry_envelope")
    if not checks.get("visual_manifest", False):
        errors.append("visual_evidence_incomplete")
    if not errors and not warnings:
        decision = "READY_FOR_S3_FINAL_REVIEW"
    elif "geometry_envelope" in errors:
        decision = "SUBMITTED_S3_R0_GEOMETRY_ENVELOPE_FAILED"
    elif "visual_evidence_incomplete" in errors:
        decision = "SUBMITTED_S3_R0_VISUAL_EVIDENCE_INCOMPLETE"
    else:
        decision = "SUBMITTED_S3_R0_PLAYBACK_READY_VALIDATION_INCOMPLETE"
    protocol_checks = [name for name in checks if name.endswith("_protocol") or name.endswith("_raw_polynomials") or name.endswith("_dynamic_attitude") or name.endswith("_quaternion_wxyz") or name.endswith("_rotation_contract") or name.endswith("_world_ee_b_to_a0_contract") or name == "authoritative_s2_baseline" or name.startswith("scene_contract")]
    environment_checks = ["python_311_environment", "isaaclab_import", "isaacsim_import", "physx_smoke"]
    asset_manifest = root / "docs/evidence/S3-R0/assets/usd_manifest.json"
    asset_imported = False
    if asset_manifest.is_file():
        asset_imported = bool(json.loads(asset_manifest.read_text(encoding="utf-8")).get("import_status"))
    playback_ok = bool(
        playback
        and checks.get("playback_runs")
        and checks.get("time_alignment")
        and checks.get("complete_duration")
        and checks.get("arm_fk_error")
        and checks.get("world_ee_error")
        and checks.get("exact_sampled_proxy_clearance")
    )
    numeric_contract_ok = all(checks.get(name, False) for name in ("isaac_aabb_clearance_gate", "state_replay_s2_clearance_delta", "s2_points_contained_by_isaac_aabbs", "framewise_conservative_order"))
    repeat_gui_ok = numeric_contract_ok and checks.get("nominal_x3", False) and checks.get("nominal_repeat", False) and checks.get("nominal_gui_contract", False) and checks.get("repeat_gui_contract", False) and checks.get("visual_manifest", False) and checks.get("isaac_scene_aabb_readback", False)
    return {
        "decision": decision,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "protocol_ready": all(checks.get(name, False) for name in protocol_checks),
        "isaac_ready": all(checks.get(name, False) for name in environment_checks),
        "robot_asset_import": asset_imported,
        "scene_load": checks.get("scene_contract", False),
        "playback_runs": playback_ok,
        "arm_fk": bool(playback and checks.get("arm_fk_error", False)),
        "world_ee_fk": bool(playback and checks.get("world_ee_error", False)),
        "clearance_exact_distance": checks.get("exact_sampled_proxy_clearance", False),
        "s2_clearance_delta": checks.get("state_replay_s2_clearance_delta", False),
        "isaac_aabb_clearance_gate": checks.get("isaac_aabb_clearance_gate", False) and checks.get("isaac_scene_aabb_readback", False),
        "state_replay_s2_clearance_delta": checks.get("state_replay_s2_clearance_delta", False),
        "s2_points_contained_by_isaac_aabbs": checks.get("s2_points_contained_by_isaac_aabbs", False),
        "framewise_conservative_order": checks.get("framewise_conservative_order", False),
        "geometry_representation_delta_reported": checks.get("geometry_representation_delta_reported", False),
        "visual_contract": visual_contract,
        "repeat_gui_visuals": repeat_gui_ok,
        "s3_kinematic_playback_accepted": playback_ok and numeric_contract_ok and checks.get("nominal_gui_contract", False) and checks.get("repeat_gui_contract", False),
        "full_closed_chain_dynamics": False,
        "s4_dynamic_articulation_ready": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(payload, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
