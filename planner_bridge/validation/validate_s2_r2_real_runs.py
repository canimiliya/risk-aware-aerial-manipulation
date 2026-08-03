"""Independent validation for captured S2-R2 AM-Planner polynomial messages."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from planner_bridge.export.sampling import load_captured_message, message_contract, sample_message
from planner_bridge.scenes.generate_s2_r2_crossarm_map import build_points


VARIANTS = {
    "smoke_free": "smoke_free_run_08",
    "loose": "loose_run_01",
    "nominal": "nominal_run_01",
    "nominal_repeat": "nominal_repeat_01",
    "narrow": "narrow_diagnostic_01",
}
FREQUENCIES = {"100Hz": 0.01, "200Hz": 0.005, "400Hz": 0.0025}


def _finite_summary(sampled: dict[str, np.ndarray]) -> dict[str, object]:
    values = np.concatenate([sampled["position"].ravel(), sampled["velocity"].ravel(), sampled["acceleration"].ravel()])
    return {
        "sample_count": int(len(sampled["time"])),
        "finite": bool(np.all(np.isfinite(values))),
        "position_min_m": sampled["position"].min(axis=0).tolist(),
        "position_max_m": sampled["position"].max(axis=0).tolist(),
        "max_speed_m_s": float(np.linalg.norm(sampled["velocity"], axis=1).max()),
        "max_acceleration_m_s2": float(np.linalg.norm(sampled["acceleration"], axis=1).max()),
        "path_length_m": float(np.linalg.norm(np.diff(sampled["position"], axis=0), axis=1).sum()),
        "start_position_m": sampled["position"][0].tolist(),
        "end_position_m": sampled["position"][-1].tolist(),
    }


def _proxy_clearance(sampled: dict[str, np.ndarray], points: np.ndarray, radius: float) -> float:
    # This is a conservative point-cloud proxy check, not a mesh collision proof.
    distances = np.linalg.norm(sampled["position"][:, None, :] - points[None, :, :], axis=2)
    return float(distances.min() - radius)


def validate_variant(runtime_root: Path, variant: str, run_id: str) -> dict[str, object]:
    source = runtime_root / run_id
    base = load_captured_message(source / "trajectory.json")
    arm = load_captured_message(source / "trajectory_arm.json")
    base_contract = message_contract(base)
    arm_contract = message_contract(arm)
    scene_variant = "smoke_free" if variant == "smoke_free" else ("nominal" if variant == "nominal_repeat" else variant)
    points = np.asarray(build_points(scene_variant), dtype=np.float64)
    result: dict[str, object] = {
        "variant": variant,
        "run_id": run_id,
        "message_contract": {"base": base_contract, "arm": arm_contract},
        "frequencies": {},
        "direction_constraint": {
            "status": "not_encoded_in_PolynomialTrajectory",
            "error_m": None,
            "note": "Mode-2 axis semantics are validated from the official inter_info contract; the ROS polynomial message does not carry the original axis flag/vector, so no invented direction error is reported."
        },
    }
    for label, dt in FREQUENCIES.items():
        base_sampled = sample_message(base, dt)
        arm_sampled = sample_message(arm, dt)
        result["frequencies"][label] = {
            "sample_dt_s": dt,
            "base": _finite_summary(base_sampled),
            "arm_cartesian": _finite_summary(arm_sampled),
            "proxy_clearance": {
                "base_radius_m": 0.08,
                "arm_radius_m": 0.025,
                "base_min_clearance_m": _proxy_clearance(base_sampled, points, 0.08),
                "arm_min_clearance_m": _proxy_clearance(arm_sampled, points, 0.025),
            },
        }
    return result


def _repeat_delta(first: dict[str, object], repeat: dict[str, object]) -> dict[str, object]:
    f = first["frequencies"]["100Hz"]["base"]
    r = repeat["frequencies"]["100Hz"]["base"]
    fa = first["frequencies"]["100Hz"]["arm_cartesian"]
    ra = repeat["frequencies"]["100Hz"]["arm_cartesian"]
    return {
        "total_duration_abs_delta_s": abs(float(f["message_contract_total_duration_s"]) - float(r["message_contract_total_duration_s"])) if "message_contract_total_duration_s" in f else None,
        "base_start_abs_delta_m": float(np.linalg.norm(np.asarray(f["start_position_m"]) - np.asarray(r["start_position_m"]))),
        "base_end_abs_delta_m": float(np.linalg.norm(np.asarray(f["end_position_m"]) - np.asarray(r["end_position_m"]))),
        "arm_start_abs_delta_m": float(np.linalg.norm(np.asarray(fa["start_position_m"]) - np.asarray(ra["start_position_m"]))),
        "arm_end_abs_delta_m": float(np.linalg.norm(np.asarray(fa["end_position_m"]) - np.asarray(ra["end_position_m"]))),
        "contract_match": first["message_contract"] == repeat["message_contract"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, default=Path("docs/evidence/S2-R2/runtime"))
    parser.add_argument("--output", type=Path, default=Path("docs/evidence/S2-R2/validation/real_run_validation.json"))
    args = parser.parse_args()
    variants = {name: validate_variant(args.runtime_root, name, run_id) for name, run_id in VARIANTS.items()}
    # Keep the repeat comparison explicit and machine-readable. Duration is taken
    # from the message contract rather than an inferred sampled endpoint.
    first = variants["nominal"]
    repeat = variants["nominal_repeat"]
    first["frequencies"]["100Hz"]["base"]["message_contract_total_duration_s"] = first["message_contract"]["base"]["total_duration"]
    repeat["frequencies"]["100Hz"]["base"]["message_contract_total_duration_s"] = repeat["message_contract"]["base"]["total_duration"]
    output = {"validator": "planner_bridge.validation.validate_s2_r2_real_runs", "variants": variants, "nominal_repeat": _repeat_delta(first, repeat)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "variants": sorted(variants), "frequencies_hz": [100, 200, 400]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
