"""Independent validation for captured S2-R2 AM-Planner polynomial messages."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
import yaml
from scipy.spatial import cKDTree

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
GATE_M = 0.010
BASE_PROXY_RADIUS_M = 0.08
END_EFFECTOR_PROXY_RADIUS_M = 0.025
ROTOR_DISK_RADIUS_M = 0.25
ROTOR_Z_OFFSET_M = 0.05
THRESHOLD_SENSITIVITY_M = (0.02, 0.05, 0.10)


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


def _clearance_details(sampled: dict[str, np.ndarray], points: np.ndarray, radius: float) -> dict[str, object]:
    # This is a conservative point-cloud proxy check, not a mesh collision proof.
    distances, nearest_indices = cKDTree(points).query(sampled["position"], k=1)
    sample_index = int(np.argmin(distances))
    point_index = int(nearest_indices[sample_index])
    return {
        "min_clearance_m": float(distances[sample_index] - radius),
        "time_s": float(sampled["time"][sample_index]),
        "obstacle_point_m": points[point_index].tolist(),
        "proxy_radius_m": radius,
    }


def _load_task_waypoints() -> tuple[np.ndarray, list[list[float]]]:
    task_path = Path(__file__).resolve().parents[1] / "scenes" / "s2_r2_tasks.yaml"
    task = yaml.safe_load(task_path.read_text(encoding="utf-8"))["nominal"]
    start = np.asarray(task["start_pt"], dtype=np.float64)
    end = np.asarray(task["end_pt"], dtype=np.float64)
    expected = [start]
    for row in task["inter_points"]:
        point = np.asarray(row[1:4], dtype=np.float64)
        # Official se3_planner.cc mode-2 semantics: flag 0 uses +Z; otherwise
        # the supplied axis vector is scaled by the 0.15 m approach offset.
        if int(row[7]) == 0:
            point = point + np.array([0.0, 0.0, 0.15])
        else:
            point = point + 0.15 * np.asarray(row[8:11], dtype=np.float64)
        expected.append(point)
    expected.append(end)
    return np.asarray(expected), task["inter_points"]


def _parse_jps_segments(log_path: Path) -> np.ndarray:
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    pattern = re.compile(
        r"Searching path from \(\s*([-+0-9.eE]+),\s*([-+0-9.eE]+),\s*([-+0-9.eE]+)\)"
        r" to \(\s*([-+0-9.eE]+),\s*([-+0-9.eE]+),\s*([-+0-9.eE]+)\)"
    )
    segments = []
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.search(ansi.sub("", line))
        if match:
            values = np.asarray([float(value) for value in match.groups()], dtype=np.float64)
            segments.append(values.reshape(2, 3))
    return np.asarray(segments, dtype=np.float64)


def _direction_validation(source: Path, inter_points: list[list[float]]) -> dict[str, object]:
    expected, _ = _load_task_waypoints()
    observed = _parse_jps_segments(source / "roslaunch.log")
    if len(observed) != len(expected) - 1:
        return {
            "status": "JPS_SEGMENT_LOG_INCOMPLETE",
            "expected_segment_count": len(expected) - 1,
            "observed_segment_count": int(len(observed)),
            "continuous_polynomial_direction_error_m": None,
        }
    endpoint_errors = np.linalg.norm(observed[:, 0] - expected[:-1], axis=1).tolist()
    endpoint_errors += np.linalg.norm(observed[:, 1] - expected[1:], axis=1).tolist()
    angle_errors = []
    for actual, target in zip(observed, zip(expected[:-1], expected[1:])):
        actual_vector = actual[1] - actual[0]
        expected_vector = np.asarray(target[1]) - np.asarray(target[0])
        actual_horizontal = actual_vector[:2]
        expected_horizontal = expected_vector[:2]
        if np.linalg.norm(actual_horizontal) < 1e-12 or np.linalg.norm(expected_horizontal) < 1e-12:
            angle_errors.append(None)
            continue
        cosine = np.dot(actual_horizontal, expected_horizontal) / (np.linalg.norm(actual_horizontal) * np.linalg.norm(expected_horizontal))
        angle_errors.append(float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))))
    labels = ["approach", "insertion", "pull", "buffer_1", "buffer_2", "retreat_1", "retreat_2"]
    segments = []
    for index, (actual, target, error) in enumerate(zip(observed, zip(expected[:-1], expected[1:]), angle_errors)):
        segments.append({
            "name": labels[index],
            "expected_start_m": np.asarray(target[0]).tolist(),
            "expected_end_m": np.asarray(target[1]).tolist(),
            "observed_start_m": actual[0].tolist(),
            "observed_end_m": actual[1].tolist(),
            "endpoint_error_max_m": float(max(np.linalg.norm(actual[0] - target[0]), np.linalg.norm(actual[1] - target[1]))),
            "horizontal_direction_error_deg": error,
        })
    return {
        "status": "EQUIVALENT_HORIZONTAL_DIRECTION_CONSTRAINT",
        "source": "official se3_planner JPS log plus task mode-2 axis semantics",
        "expected_segment_count": len(expected) - 1,
        "observed_segment_count": int(len(observed)),
        "jps_endpoint_error_max_m": float(max(endpoint_errors)),
        "jps_horizontal_direction_error_max_deg": float(max(value for value in angle_errors if value is not None)),
        "segments": segments,
        "continuous_polynomial_direction_error_m": None,
        "note": "PolynomialTrajectory does not carry the original mode-2 flag/vector; this validates the equivalent horizontal JPS direction and the source-grounded +Z offset, without inventing a continuous tool-axis error.",
    }


def _threshold_sensitivity(clearance_m: float) -> dict[str, object]:
    return {f"{threshold:.2f}m": {"threshold_m": threshold, "pass": bool(clearance_m >= threshold)} for threshold in THRESHOLD_SENSITIVITY_M}


def validate_variant(runtime_root: Path, variant: str, run_id: str) -> dict[str, object]:
    source = runtime_root / run_id
    base = load_captured_message(source / "trajectory.json")
    arm = load_captured_message(source / "trajectory_arm.json")
    base_contract = message_contract(base)
    arm_contract = message_contract(arm)
    scene_variant = "smoke_free" if variant == "smoke_free" else ("nominal" if variant == "nominal_repeat" else variant)
    points = np.asarray(build_points(scene_variant), dtype=np.float64)
    direction = _direction_validation(source, _load_task_waypoints()[1])
    result: dict[str, object] = {
        "variant": variant,
        "run_id": run_id,
        "message_contract": {"base": base_contract, "arm": arm_contract},
        "frequencies": {},
        "direction_constraint": direction,
        "reconstruction_contract": {
            "end_effector_world": "p_WB + R_WB * p_A0E; captured output has yaw=0 and no roll/pitch channel, so R_WB=I for this reconstruction",
            "joint_trajectory": "not reconstructed; no official time-parameterized IK executor was found",
        },
    }
    for label, dt in FREQUENCIES.items():
        base_sampled = sample_message(base, dt)
        arm_sampled = sample_message(arm, dt)
        end_effector = {
            "time": base_sampled["time"],
            "position": base_sampled["position"] + arm_sampled["position"],
            "velocity": base_sampled["velocity"] + arm_sampled["velocity"],
            "acceleration": base_sampled["acceleration"] + arm_sampled["acceleration"],
        }
        base_clearance = _clearance_details(base_sampled, points, BASE_PROXY_RADIUS_M)
        end_effector_clearance = _clearance_details(end_effector, points, END_EFFECTOR_PROXY_RADIUS_M)
        rotor_sampled = {
            "time": base_sampled["time"],
            "position": base_sampled["position"] + np.array([0.0, 0.0, ROTOR_Z_OFFSET_M]),
        }
        rotor_clearance = _clearance_details(rotor_sampled, points, ROTOR_DISK_RADIUS_M)
        gated_clearance = min(base_clearance["min_clearance_m"], end_effector_clearance["min_clearance_m"])
        hazard = base_clearance if base_clearance["min_clearance_m"] <= end_effector_clearance["min_clearance_m"] else end_effector_clearance
        result["frequencies"][label] = {
            "sample_dt_s": dt,
            "base": _finite_summary(base_sampled),
            "arm_cartesian": _finite_summary(arm_sampled),
            "end_effector_world": _finite_summary(end_effector),
            "proxy_clearance": {
                "base_radius_m": BASE_PROXY_RADIUS_M,
                "end_effector_world_radius_m": END_EFFECTOR_PROXY_RADIUS_M,
                "base_min_clearance_m": base_clearance["min_clearance_m"],
                "base_hazard": base_clearance,
                "end_effector_world_min_clearance_m": end_effector_clearance["min_clearance_m"],
                "end_effector_world_hazard": end_effector_clearance,
                "gated_min_clearance_m": gated_clearance,
                "dangerous_component": "base_body_proxy" if hazard is base_clearance else "end_effector_world_proxy",
                "dangerous_time_s": hazard["time_s"],
                "dangerous_obstacle_point_m": hazard["obstacle_point_m"],
                "threshold_sensitivity": _threshold_sensitivity(gated_clearance),
                "component_checks": {
                    "base_body_proxy": {"status": "GATED", "clearance": base_clearance},
                    "end_effector_world_proxy": {"status": "GATED", "clearance": end_effector_clearance},
                    "rotor_disk_proxy": {"status": "DIAGNOSTIC_NOT_GATE_PROVISIONAL_R0", "clearance": rotor_clearance, "reason": "S2-R0 provisional rotor radius is not an accepted AM-Planner collision contract"},
                    "arm_links": {"status": "NOT_EVALUATED_NO_OFFICIAL_IK", "reason": "continuous joint/link geometry cannot be reconstructed from Cartesian trajectory alone"},
                },
            },
        }
    return result


def _repeat_delta(first: dict[str, object], repeat: dict[str, object]) -> dict[str, object]:
    f = first["frequencies"]["100Hz"]["base"]
    r = repeat["frequencies"]["100Hz"]["base"]
    fa = first["frequencies"]["100Hz"]["arm_cartesian"]
    ra = repeat["frequencies"]["100Hz"]["arm_cartesian"]
    fe = first["frequencies"]["100Hz"]["end_effector_world"]
    re = repeat["frequencies"]["100Hz"]["end_effector_world"]
    return {
        "total_duration_abs_delta_s": abs(float(f["message_contract_total_duration_s"]) - float(r["message_contract_total_duration_s"])) if "message_contract_total_duration_s" in f else None,
        "base_start_abs_delta_m": float(np.linalg.norm(np.asarray(f["start_position_m"]) - np.asarray(r["start_position_m"]))),
        "base_end_abs_delta_m": float(np.linalg.norm(np.asarray(f["end_position_m"]) - np.asarray(r["end_position_m"]))),
        "arm_start_abs_delta_m": float(np.linalg.norm(np.asarray(fa["start_position_m"]) - np.asarray(ra["start_position_m"]))),
        "arm_end_abs_delta_m": float(np.linalg.norm(np.asarray(fa["end_position_m"]) - np.asarray(ra["end_position_m"]))),
        "end_effector_start_abs_delta_m": float(np.linalg.norm(np.asarray(fe["start_position_m"]) - np.asarray(re["start_position_m"]))),
        "end_effector_end_abs_delta_m": float(np.linalg.norm(np.asarray(fe["end_position_m"]) - np.asarray(re["end_position_m"]))),
        "nominal_gated_min_clearance_abs_delta_m": abs(float(first["frequencies"]["100Hz"]["proxy_clearance"]["gated_min_clearance_m"]) - float(repeat["frequencies"]["100Hz"]["proxy_clearance"]["gated_min_clearance_m"])),
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
