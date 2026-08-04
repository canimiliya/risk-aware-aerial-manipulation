from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

from planner_bridge.execution.full_body_proxy import T_B_A0
from planner_bridge.execution.official_delta_kinematics import official_ik
from planner_bridge.execution.playback_validator import validate_attitude
from planner_bridge.protocol.frames import TOOL_DIRECTION_A0, compose_world_ee, transform_tool_direction
from planner_bridge.protocol.phases import phase_for_progress
from planner_bridge.protocol.polynomial import sample_message
from planner_bridge.protocol.validation import validate_bundle

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "nominal_100w0": ROOT / "docs/evidence/S2-R6/runtime/nominal_100w0",
    "nominal_repeat_100w0": ROOT / "docs/evidence/S2-R6/runtime/nominal_repeat_final_100w0",
}
S2_YAW_DOT_RAD_S = 0.01


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _raw_message(path: Path) -> dict:
    return _read(path / "trajectory.json")["message"]


def _s2_attitude(base: dict[str, np.ndarray], source_message: dict) -> tuple[dict, dict[str, np.ndarray]]:
    start_yaw = float(source_message.get("start_yaw", 0.0))
    final_yaw = float(source_message.get("final_yaw", start_yaw))
    yaw = start_yaw + (final_yaw - start_yaw) * base["phase_progress"]
    yaw_dot = np.full(len(base["time"]), S2_YAW_DOT_RAD_S, dtype=float)
    return validate_attitude(
        {
            "velocity": base["velocity"],
            "acceleration": base["acceleration"],
            "jerk": base["jerk"],
            "yaw": yaw,
            "yaw_dot": yaw_dot,
        }
    )


def _legacy_record(output: Path) -> dict[str, object]:
    trajectory = output / "trajectory.json"
    manifest = output / "sha256_manifest.json"
    relative_trajectory = trajectory.relative_to(ROOT).as_posix()
    relative_manifest = manifest.relative_to(ROOT).as_posix()
    old_trajectory = subprocess.run(["git", "show", f"HEAD:{relative_trajectory}"], cwd=ROOT, capture_output=True, check=False).stdout
    old_manifest = subprocess.run(["git", "show", f"HEAD:{relative_manifest}"], cwd=ROOT, capture_output=True, check=False).stdout
    if not old_trajectory and not trajectory.is_file():
        return {"present": False}
    legacy_bytes = old_trajectory or trajectory.read_bytes()
    legacy = json.loads(legacy_bytes.decode("utf-8"))
    validator_errors = validate_bundle(legacy)
    return {
        "present": True,
        "trajectory_path": str(trajectory),
        "source": "git HEAD bytes" if old_trajectory else "existing local bytes",
        "trajectory_sha256": hashlib.sha256(legacy_bytes).hexdigest(),
        "manifest_sha256": hashlib.sha256(old_manifest or (manifest.read_bytes() if manifest.is_file() else b"")).hexdigest() if (old_manifest or manifest.is_file()) else None,
        "validator_rejected": bool(validator_errors),
        "validator_rejection_error_count": len(validator_errors),
        "validator_rejection_error_examples": validator_errors[:12],
        "identity_quaternion_field": "base_quaternion_xyzw",
        "identity_quaternion": [0.0, 0.0, 0.0, 1.0],
        "migration": "Legacy 200 Hz identity/zero-omega bundle was replaced by S2 OfficialFlatnessMap WXYZ attitude, B->A0 world composition, and transformed tool direction. The legacy bytes are represented by these SHA-256 values; no S2 source trajectory was changed.",
    }


def export_variant(name: str, source: Path, output: Path) -> dict:
    base_payload = _read(source / "trajectory.json")
    arm_payload = _read(source / "trajectory_arm.json")
    base = sample_message(base_payload, 200.0)
    arm = sample_message(arm_payload, 200.0)
    if not np.allclose(base["time"], arm["time"], atol=1e-12, rtol=0.0):
        raise ValueError(f"base/arm time grids differ for {name}")
    q = np.asarray([official_ik(point) for point in arm["position"]], dtype=float)
    if not np.isfinite(q).all():
        raise ValueError(f"official IK returned non-finite values for {name}")
    if len(q) < 3:
        raise ValueError("canonical trajectory is too short for q derivatives")
    qdot = np.gradient(q, base["time"], axis=0, edge_order=2)
    qddot = np.gradient(qdot, base["time"], axis=0, edge_order=2)
    attitude_summary, attitude = _s2_attitude(base, base_payload["message"])
    frames = []
    for i, time in enumerate(base["time"]):
        phase_id, _, phase_progress = phase_for_progress(float(base["phase_progress"][i]))
        rotation_wb = attitude["rotation"][i]
        tool_direction_w = transform_tool_direction(rotation_wb, TOOL_DIRECTION_A0, T_B_A0)
        frames.append(
            {
                "time": float(time),
                "segment_id": int(base["segment_id"][i]),
                "base_position_m": base["position"][i].tolist(),
                "base_quaternion_WB_wxyz": attitude["quaternion"][i].tolist(),
                "base_velocity_m_s": base["velocity"][i].tolist(),
                "base_acceleration_m_s2": base["acceleration"][i].tolist(),
                "base_jerk_m_s3": base["jerk"][i].tolist(),
                "base_body_omega_B_rad_s": attitude["omega"][i].tolist(),
                "base_thrust_N": float(attitude["thrust"][i]),
                "arm_cartesian_position_m": arm["position"][i].tolist(),
                "arm_cartesian_velocity_m_s": arm["velocity"][i].tolist(),
                "arm_cartesian_acceleration_m_s2": arm["acceleration"][i].tolist(),
                "q_rad": q[i].tolist(),
                "qdot_rad_s": qdot[i].tolist(),
                "qddot_rad_s2": qddot[i].tolist(),
                "world_ee_position_m": compose_world_ee(base["position"][i], arm["position"][i], rotation_wb, T_B_A0).tolist(),
                "tool_direction_status": "EQUIVALENT_HORIZONTAL_DIRECTION_CONSTRAINT",
                "tool_direction_A0": TOOL_DIRECTION_A0.tolist(),
                "tool_direction_W": tool_direction_w.tolist(),
                "phase_id": phase_id,
                "phase_progress": phase_progress,
            }
        )
    bundle = {
        "protocol": "S3-R0-trajectory-protocol-v1",
        "variant": name,
        "sample_hz": 200,
        "source": {
            "allowed_lineage": "S2-R6",
            "raw_base_polynomial": "raw_base_polynomial.json",
            "raw_arm_polynomial": "raw_arm_polynomial.json",
            "base_source": str(source / "trajectory.json"),
            "arm_source": str(source / "trajectory_arm.json"),
        },
        "scene_contract": {
            "base_frame": "world",
            "arm_frame": "A0",
            "a0_origin": "T_B_A0 from planner_bridge.execution.full_body_proxy",
            "T_B_A0_rotation_translation": T_B_A0.tolist(),
            "world_ee": "p_WB_plus_R_WB_(R_BA0_p_A0E_plus_t_BA0)",
            "base_quaternion_order": "wxyz",
            "tool_direction_mapping": "R_WB @ R_BA0 @ tool_direction_A0",
            "playback_mode": "REFERENCE_STATE_PLAYBACK",
        },
        "derivation": {
            "q": "project official_ik(arm_cartesian_position)",
            "qdot_qddot": "second-order finite differences on canonical raw-polynomial time grid",
            "base_attitude": "OfficialFlatnessMap reused through playback_validator.validate_attitude",
            "attitude_source": "S2_OFFICIAL_FLATNESS_MAP_RECONSTRUCTION",
            "yaw_convention": "linear interpolation of source start_yaw/final_yaw",
            "yaw_dot_convention": "S2 playback constant 0.01 rad/s",
            "quaternion_order": "base_quaternion_WB_wxyz",
            "world_ee": "p_WB + R_WB @ (R_BA0 @ p_A0E + t_BA0)",
            "tool_direction": "direction only; complete end-effector quaternion intentionally not provided",
        },
        "frames": frames,
    }
    errors = validate_bundle(bundle)
    if errors:
        raise ValueError(f"invalid generated bundle: {errors[:10]}")
    output.mkdir(parents=True, exist_ok=True)
    (output / "trajectory.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "raw_base_polynomial.json").write_text(json.dumps(base_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "raw_arm_polynomial.json").write_text(json.dumps(arm_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file() and p.name != "sha256_manifest.json"}
    (output / "sha256_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"variant": name, "samples": len(frames), "duration_s": frames[-1]["time"], "attitude": attitude_summary, "files": manifest}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT / "data/trajectories/S3-R0")
    args = parser.parse_args()
    legacy = {name: _legacy_record(args.output_root / name) for name in SOURCES}
    summaries = [export_variant(name, source, args.output_root / name) for name, source in SOURCES.items()]
    correction = {
        "protocol": "S3-R0-trajectory-protocol-v1",
        "correction": "S3-R0-R3姿态时间轴精确距离修正",
        "legacy_identity_bundles": legacy,
        "new_contract": {
            "base_quaternion": "base_quaternion_WB_wxyz",
            "base_body_omega": "base_body_omega_B_rad_s",
            "base_thrust": "base_thrust_N",
            "attitude_source": "S2_OFFICIAL_FLATNESS_MAP_RECONSTRUCTION",
            "world_ee": "p_WB + R_WB @ (R_BA0 @ p_A0E + t_BA0)",
            "tool_direction": "R_WB @ R_BA0 @ direction_A0",
        },
        "variants": [{"variant": item["variant"], "trajectory_sha256": item["files"]["trajectory.json"]} for item in summaries],
    }
    evidence = ROOT / "docs/evidence/S3-R0/protocol_v1_frame_correction.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(correction, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": "PASS", "variants": summaries, "correction_evidence": str(evidence)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
