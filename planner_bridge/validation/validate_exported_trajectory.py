"""Validate the S1-R2 raw/CSV/NPZ polynomial export contract."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from planner_bridge.export.sampling import _axis_coefficients, _evaluate, csv_matrix, load_captured_message, message_contract, sample_message


CONTINUITY_TOLERANCE = 1e-8


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_topic(directory: Path, suffix: str = "") -> dict:
    raw = load_captured_message(directory / f"raw_trajectory{suffix}.json")
    contract = message_contract(raw)
    sampled = sample_message(raw, float(json.loads((directory / "metadata.json").read_text(encoding="utf-8"))["sample_dt"]))
    csv_path = directory / f"sampled_trajectory{suffix}.csv"
    npz_path = directory / f"sampled_trajectory{suffix}.npz"
    csv_values = csv_matrix(csv_path)
    npz = np.load(npz_path)
    expected_matrix = np.column_stack([
        sampled["time"], sampled["segment_id"], sampled["segment_local_time"], sampled["u"],
        sampled["position"], sampled["velocity"], sampled["acceleration"],
    ])
    checks = {
        "message_type": contract["message_type"] == "quadrotor_msgs/PolynomialTrajectory",
        "segment_duration_positive": all(value > 0 for value in contract["durations"]),
        "coefficient_lengths_match": contract["expected_coefficients_per_axis"] == contract["actual_coefficients_per_axis"]["x"] == contract["actual_coefficients_per_axis"]["y"] == contract["actual_coefficients_per_axis"]["z"],
        "raw_coefficients_finite": bool(all(np.isfinite(raw["message"][f"coef_{axis}"]).all() for axis in "xyz")),
        "raw_time_finite": bool(np.isfinite(raw["message"]["time"]).all()),
        "sampled_values_finite": bool(np.isfinite(expected_matrix).all()),
        "csv_npz_consistent": bool(np.allclose(csv_values, expected_matrix, rtol=0.0, atol=1e-12)),
        "npz_keys_complete": set(npz.files) == set(sampled),
        "sampled_duration_matches": bool(np.isclose(float(sampled["time"][-1]), contract["total_duration"], rtol=0.0, atol=1e-12)),
        "first_sample_at_zero": bool(np.isclose(float(sampled["time"][0]), 0.0, rtol=0.0, atol=1e-12)),
        "last_sample_not_duplicated": len(np.unique(sampled["time"])) == len(sampled["time"]),
    }
    boundary_rows = []
    durations = [float(value) for value in contract["durations"]]
    cumulative = np.cumsum(np.asarray(durations, dtype=float))
    msg = raw["message"]
    for segment, boundary in enumerate(cumulative[:-1]):
        left_values = []
        right_values = []
        for axis in "xyz":
            left_coeff = _axis_coefficients(msg, segment, axis)
            right_coeff = _axis_coefficients(msg, segment + 1, axis)
            left_values.append([_evaluate(left_coeff, 1.0, derivative, durations[segment]) for derivative in range(3)])
            right_values.append([_evaluate(right_coeff, 0.0, derivative, durations[segment + 1]) for derivative in range(3)])
        left_values = np.asarray(left_values, dtype=float)
        right_values = np.asarray(right_values, dtype=float)
        delta = {
            "position": float(np.max(np.abs(left_values[:, 0] - right_values[:, 0]))),
            "velocity": float(np.max(np.abs(left_values[:, 1] - right_values[:, 1]))),
            "acceleration": float(np.max(np.abs(left_values[:, 2] - right_values[:, 2]))),
        }
        boundary_rows.append({"boundary_time": float(boundary), "delta": delta})
    checks["boundary_continuity_position"] = all(item["delta"]["position"] <= CONTINUITY_TOLERANCE for item in boundary_rows)
    checks["boundary_continuity_velocity"] = all(item["delta"]["velocity"] <= CONTINUITY_TOLERANCE for item in boundary_rows)
    checks["boundary_continuity_acceleration"] = all(item["delta"]["acceleration"] <= CONTINUITY_TOLERANCE for item in boundary_rows)
    checks["boundary_continuity_tolerance"] = CONTINUITY_TOLERANCE
    return {
        "checks": checks,
        "segment_count": contract["num_segment"],
        "total_duration": contract["total_duration"],
        "sample_count": len(sampled["time"]),
        "nan_count": int(np.isnan(expected_matrix).sum()),
        "inf_count": int(np.isinf(expected_matrix).sum()),
        "boundary_rows": boundary_rows,
    }


def validate_directory(directory: Path) -> dict:
    base = validate_topic(directory)
    arm = validate_topic(directory, "_arm")
    manifest_lines = (directory / "sha256_manifest.txt").read_text(encoding="utf-8").splitlines()
    manifest_ok = True
    for line in manifest_lines:
        digest, name = line.split("  ", 1)
        manifest_ok &= (directory / name).is_file() and sha256(directory / name) == digest
    checks = {
        "base": base,
        "arm": arm,
        "sha_manifest_complete": manifest_ok,
        "all_checks_pass": all(base["checks"].values()) and all(arm["checks"].values()) and manifest_ok,
    }
    result = {
        "status": "PASS" if checks["all_checks_pass"] else "FAIL",
        "continuity_tolerance": CONTINUITY_TOLERANCE,
        "checks": checks,
    }
    (directory / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directories", type=Path, nargs="+")
    args = parser.parse_args()
    results = {str(directory): validate_directory(directory) for directory in args.directories}
    print(json.dumps({key: value["status"] for key, value in results.items()}, ensure_ascii=False))
    return 0 if all(value["status"] == "PASS" for value in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
