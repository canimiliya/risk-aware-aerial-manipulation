#!/usr/bin/env python3
"""Independent S1-R2 trajectory export/waypoint/video audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


OFFICIAL = ("write_official", "grasp_official", "lift_official", "grasp_repeat")
REQUIRED = (
    "metadata.json", "raw_trajectory.json", "raw_trajectory_arm.json",
    "sampled_trajectory.csv", "sampled_trajectory_arm.csv",
    "sampled_trajectory.npz", "sampled_trajectory_arm.npz",
    "validation.json", "sha256_manifest.txt",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return result.returncode, (result.stdout + result.stderr).strip()


def audit_export(directory: Path) -> dict:
    missing = [name for name in REQUIRED if not (directory / name).is_file()]
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8")) if not missing else {}
    validation = json.loads((directory / "validation.json").read_text(encoding="utf-8")) if not missing else {}
    return {
        "directory": str(directory).replace("\\", "/"),
        "missing_files": missing,
        "validation_status": validation.get("status"),
        "message_type": metadata.get("message_type"),
        "git_commit": metadata.get("git_commit"),
        "am_planner_commit": metadata.get("am_planner_commit"),
        "sample_frequency_hz": metadata.get("sample_frequency_hz"),
        "segment_count": metadata.get("segment_count"),
        "total_duration": metadata.get("total_duration"),
        "all_files_under_10mb": all(path.stat().st_size <= 10 * 1024 * 1024 for path in directory.rglob("*") if path.is_file()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo.resolve()
    errors: list[str] = []
    checks: dict[str, object] = {}

    contract_files = [
        root / "docs/evidence/S1-R2/message_contract/message_definition.txt",
        root / "docs/evidence/S1-R2/message_contract/field_semantics.md",
        root / "docs/evidence/S1-R2/message_contract/polynomial_order.md",
        root / "docs/evidence/S1-R2/message_contract/unavailable_fields.md",
        root / "docs/trajectory_contract.md",
    ]
    checks["message_contract"] = {
        "files_present": all(path.is_file() for path in contract_files),
        "message_type": "quadrotor_msgs/PolynomialTrajectory",
        "required_fields_documented": all(token in (root / "docs/evidence/S1-R2/message_contract/message_definition.txt").read_text(encoding="utf-8") for token in ("coef_x", "coef_y", "coef_z", "time", "order")) if contract_files[0].is_file() else False,
        "unavailable_fields_documented": contract_files[3].is_file(),
    }
    if not all(checks["message_contract"].values()):
        errors.append("message contract evidence is incomplete")

    export_root = root / "data/trajectories/S1-R2"
    export_checks = [audit_export(export_root / name) for name in OFFICIAL]
    variant_check = audit_export(export_root / "grasp_waypoint_variant_01")
    checks["official_exports"] = export_checks
    checks["waypoint_variant_export"] = variant_check
    for item in export_checks + [variant_check]:
        if item["missing_files"] or item["validation_status"] != "PASS":
            errors.append(f"export validation failed: {item['directory']}")
        if item["message_type"] != "quadrotor_msgs/PolynomialTrajectory":
            errors.append(f"message type mismatch: {item['directory']}")
        if item["git_commit"] != "a028f265c616be922e5ab0ccff907fcbeda06273":
            errors.append(f"unexpected main commit metadata: {item['directory']}")
        if item["am_planner_commit"] != "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d":
            errors.append(f"unexpected AM-Planner commit metadata: {item['directory']}")

    variant_evidence = root / "docs/evidence/S1-R2/waypoint_variant/grasp_waypoint_variant_01"
    failed_attempts = [
        root / "docs/evidence/S1-R2/waypoint_variant/grasp_waypoint_variant_01_rosversion_fail",
        root / "docs/evidence/S1-R2/waypoint_variant/grasp_waypoint_variant_01_wrapper_crlf_fail",
    ]
    command_text = (variant_evidence / "command.txt").read_text(encoding="utf-8") if (variant_evidence / "command.txt").is_file() else ""
    variant_result = json.loads((variant_evidence / "result_summary.json").read_text(encoding="utf-8")) if (variant_evidence / "result_summary.json").is_file() else {}
    checks["waypoint_variant"] = {
        "baseline_object_px": 0.0,
        "variant_object_px": 0.05,
        "independent_launch_overlay": (root / "planner_bridge/variants/grasp_waypoint_variant_01.launch").is_file(),
        "successful_capture_exit": variant_result.get("capture_exit") == 0,
        "dual_topic_files": (variant_evidence / "trajectory.json").is_file() and (variant_evidence / "trajectory_arm.json").is_file(),
        "historical_failed_attempts_preserved": all(path.is_dir() for path in failed_attempts),
        "command_records_values": "baseline_object_px=0.00" in command_text and "variant_object_px=0.05" in command_text,
    }
    if not all(value for key, value in checks["waypoint_variant"].items() if isinstance(value, bool)):
        errors.append("waypoint variant evidence is incomplete")
    comparison = root / "docs/evidence/S1-R2/waypoint_variant_comparison.json"
    checks["waypoint_comparison"] = json.loads(comparison.read_text(encoding="utf-8")) if comparison.is_file() else {}
    if not comparison.is_file():
        errors.append("waypoint comparison is missing")

    manifest_path = root / "outputs/videos/S1-R2/video_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    manifest_entries = manifest.get("entries", [])
    manifest_ok = len(manifest_entries) == 4
    for entry in manifest_entries:
        video = manifest_path.parent / entry["file"]
        png = root / "outputs/figures/S1-R2" / Path(entry["static_png"]).name
        manifest_ok &= video.is_file() and sha256(video) == entry["sha256"] and png.is_file() and png.stat().st_size < 2 * 1024 * 1024
    checks["visualization"] = {"manifest_present": manifest_path.is_file(), "entry_count": len(manifest_entries), "files_and_hashes_ok": manifest_ok}
    if not manifest_ok:
        errors.append("video/static visualization manifest is incomplete")

    code, changed = run(["git", "diff", "main", "--name-only"], root)
    changed_paths = changed.splitlines() if code == 0 else []
    algorithm_changes = [path for path in changed_paths if path.startswith("src/") and re.search(r"\.(cpp|cc|cxx|h|hpp)$", path, re.IGNORECASE)]
    checks["algorithm_boundary"] = {"diff_exit": code, "algorithm_source_changes": algorithm_changes}
    if code != 0 or algorithm_changes:
        errors.append("algorithm source boundary check failed")

    credential_pattern = re.compile(r"(?:-----BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY-----|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{12,})")
    scan_roots = [root / "planner_bridge", root / "scripts", root / "docs/evidence/S1-R2", root / "data/trajectories/S1-R2", root / "outputs/figures/S1-R2", root / "outputs/videos/S1-R2/video_manifest.json"]
    credential_hits = []
    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        try:
            files = [scan_root] if scan_root.is_file() else [path for path in scan_root.rglob("*") if path.is_file() and not path.is_symlink()]
        except OSError:
            continue
        for path in files:
            try:
                if path.stat().st_size > 10 * 1024 * 1024:
                    continue
                if credential_pattern.search(path.read_text(encoding="utf-8", errors="replace")):
                    credential_hits.append(str(path))
            except OSError:
                continue
    large_files = []
    data_root = root / "data/trajectories/S1-R2"
    for path in data_root.rglob("*"):
        try:
            if path.is_file() and not path.is_symlink() and path.stat().st_size > 10 * 1024 * 1024:
                large_files.append(str(path))
        except OSError:
            continue
    checks["safety_scan"] = {"credential_hits": credential_hits, "large_files_in_scope": large_files}
    if credential_hits or checks["safety_scan"]["large_files_in_scope"]:
        errors.append("credential or large-file scan failed")

    checks["state"] = {"s1_r2": "SUBMITTED_FOR_REVIEW", "s1": "IN_PROGRESS", "s2_s8": "FROZEN"}
    payload = {
        "decision": "SUBMITTED_S1_R2_TRAJECTORY_EXPORT" if not errors else "REVISION_REQUIRED",
        "errors": errors,
        "warnings": [],
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": payload["decision"], "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
