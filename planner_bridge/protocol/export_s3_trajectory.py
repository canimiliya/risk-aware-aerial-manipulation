from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from planner_bridge.execution.official_delta_kinematics import official_ik
from planner_bridge.protocol.frames import compose_world_ee
from planner_bridge.protocol.phases import phase_for_progress
from planner_bridge.protocol.polynomial import sample_message
from planner_bridge.protocol.validation import validate_bundle

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "nominal_100w0": ROOT / "docs/evidence/S2-R6/runtime/nominal_100w0",
    "nominal_repeat_100w0": ROOT / "docs/evidence/S2-R6/runtime/nominal_repeat_final_100w0",
}


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _raw_message(path: Path) -> dict:
    return _read(path / "trajectory.json")["message"]


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
    qdot = np.gradient(q, base["time"], axis=0, edge_order=2)
    qddot = np.gradient(qdot, base["time"], axis=0, edge_order=2)
    base_jerk = np.gradient(base["acceleration"], base["time"], axis=0, edge_order=2)
    frames = []
    for i, time in enumerate(base["time"]):
        phase_id, _, phase_progress = phase_for_progress(float(base["phase_progress"][i]))
        frames.append({
            "time": float(time), "segment_id": int(base["segment_id"][i]),
            "base_position_m": base["position"][i].tolist(), "base_quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
            "base_velocity_m_s": base["velocity"][i].tolist(), "base_acceleration_m_s2": base["acceleration"][i].tolist(),
            "base_jerk_m_s3": base_jerk[i].tolist(), "body_angular_velocity_rad_s": [0.0, 0.0, 0.0],
            "arm_cartesian_position_m": arm["position"][i].tolist(), "arm_cartesian_velocity_m_s": arm["velocity"][i].tolist(),
            "arm_cartesian_acceleration_m_s2": arm["acceleration"][i].tolist(), "q_rad": q[i].tolist(),
            "qdot_rad_s": qdot[i].tolist(), "qddot_rad_s2": qddot[i].tolist(),
            "world_ee_position_m": compose_world_ee(base["position"][i], arm["position"][i]).tolist(),
            "tool_direction_status": "EQUIVALENT_HORIZONTAL_DIRECTION_CONSTRAINT", "phase_id": phase_id,
            "phase_progress": phase_progress,
        })
    bundle = {
        "protocol": "S3-R0-trajectory-protocol-v1", "variant": name, "sample_hz": 200,
        "source": {"allowed_lineage": "S2-R6", "raw_base_polynomial": "raw_base_polynomial.json", "raw_arm_polynomial": "raw_arm_polynomial.json", "base_source": str(source / "trajectory.json"), "arm_source": str(source / "trajectory_arm.json")},
        "scene_contract": {"base_frame": "world", "arm_frame": "A0", "a0_origin": "base_reference_origin", "world_ee": "base_position_plus_a0_arm_position", "playback_mode": "REFERENCE_STATE_PLAYBACK"},
        "derivation": {"q": "project official_ik(arm_cartesian_position)", "qdot_qddot": "second-order finite differences on canonical time grid", "base_jerk": "second-order finite differences of polynomial acceleration", "base_quaternion": "identity because source contains yaw endpoints only; no complete orientation trajectory"},
        "frames": frames,
    }
    errors = validate_bundle(bundle)
    if errors:
        raise ValueError(f"invalid generated bundle: {errors[:5]}")
    output.mkdir(parents=True, exist_ok=True)
    (output / "trajectory.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "raw_base_polynomial.json").write_text(json.dumps(base_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "raw_arm_polynomial.json").write_text(json.dumps(arm_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file() and p.name != "sha256_manifest.json"}
    (output / "sha256_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"variant": name, "samples": len(frames), "duration_s": frames[-1]["time"], "files": manifest}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT / "data/trajectories/S3-R0")
    args = parser.parse_args()
    summaries = [export_variant(name, source, args.output_root / name) for name, source in SOURCES.items()]
    print(json.dumps({"decision": "PASS", "variants": summaries}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
