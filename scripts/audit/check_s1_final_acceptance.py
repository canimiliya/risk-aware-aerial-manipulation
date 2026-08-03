from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs/evidence/S1/final_acceptance/s1_final_acceptance.json"
MAIN_MERGE = "a028f265c616be922e5ab0ccff907fcbeda06273"
AM_PLANNER_COMMIT = "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d"
EXPECTED_S1_R2_HEAD = "f12f61ab1925e30dfa31dbb4c8a2f63c023cfb0a"
OFFICIAL_EXPORTS = {
    "write": ("write_official", 19),
    "grasp": ("grasp_official", 4),
    "lift": ("lift_official", 3),
    "grasp_repeat": ("grasp_repeat", 4),
}
EXPORT_FILES = {
    "metadata.json", "raw_trajectory.json", "raw_trajectory_arm.json", "sampled_trajectory.csv",
    "sampled_trajectory_arm.csv", "sampled_trajectory.npz", "sampled_trajectory_arm.npz", "validation.json", "sha256_manifest.txt",
}


def run(root: Path = ROOT) -> dict:
    errors: list[str] = []
    limitations: list[dict[str, str]] = []
    checks: dict[str, object] = {}

    def require(label: str, ok: bool, detail: object = None) -> None:
        checks[label] = detail if detail is not None else ok
        if not ok:
            errors.append(label)

    report = root / "docs/reports/S1-R2_trajectory_export_and_waypoint_report.md"
    status = root / "docs/milestones/S1_R2_status.md"
    progress = next(root.glob("01_*_v1.4.md"))
    report_text = report.read_text(encoding="utf-8-sig")
    status_text = status.read_text(encoding="utf-8-sig")
    progress_text = progress.read_text(encoding="utf-8-sig")

    require("fixed_main_merge", MAIN_MERGE in report_text)
    require("fixed_am_planner_commit", AM_PLANNER_COMMIT in report_text or any(AM_PLANNER_COMMIT in path.read_text(encoding="utf-8-sig") for path in (root / "data/trajectories/S1-R2").glob("*/metadata.json")))
    require("report_distinguishes_commits", all(token in report_text for token in ["8d9d1da", "0fbbbe4", EXPECTED_S1_R2_HEAD]))
    require("state_documents", "S1-R2：`PASS`" in status_text and "S1：`PASS_WITH_LIMITATIONS`" in status_text and "S1-R2：`PASS`" in progress_text)

    license_path = root / "third_party/licenses/AM-Planner_LICENSE_STATUS_7ea9a0a.md"
    manifest_path = root / "docs/third_party_manifest.md"
    license_status = "README_DECLARES_MIT_LICENSE_BUT_LICENSE_FILE_UNAVAILABLE_AT_FROZEN_COMMIT"
    require("license_boundary", license_status in license_path.read_text(encoding="utf-8-sig") and license_status in manifest_path.read_text(encoding="utf-8-sig"))

    s1r1 = json.loads((root / "docs/evidence/S1-R1/final_acceptance/s1_r1_final_acceptance.json").read_text(encoding="utf-8-sig"))
    require("s1_r1_acceptance", s1r1.get("decision") == "PASS_WITH_LIMITATIONS" and not s1r1.get("errors") and not s1r1.get("unresolved_warnings"))
    limitations = s1r1.get("accepted_limitations", [])
    require("s1_r1_accepted_limitations", len(limitations) == 3, limitations)
    runtime_runs = s1r1.get("checks", {}).get("runtime_runs", {})
    require("s1_r1_four_runtime_runs", set(runtime_runs) >= {"write", "grasp", "lift", "grasp_repeat"}, sorted(runtime_runs))
    require("s1_r1_runtime_topics", all(item.get("capture_exit") == 0 and item.get("trajectory_topics_present") and item.get("trajectory_arm_topics_present") for item in runtime_runs.values()))
    abi = s1r1.get("checks", {}).get("abi", {})
    require("s1_r1_abi", abi.get("python38_occurrences") == 0 and abi.get("runtime_not_found_occurrences") == 0, abi)

    triage = root / "docs/evidence/S1-R1/final_warning_triage/catkin_warning_inventory.json"
    require("catkin_warning_inventory", triage.is_file() and json.loads(triage.read_text(encoding="utf-8-sig")).get("warning_bearing_package_count") == 8)
    require("raw_warning_review", (root / "docs/reviews/S1-R1_warning_acceptance_review_2026-08-03.md").is_file())

    export_root = root / "data/trajectories/S1-R2"
    export_checks: dict[str, object] = {}
    for label, (directory, segments) in OFFICIAL_EXPORTS.items():
        path = export_root / directory
        missing = sorted(name for name in EXPORT_FILES if not (path / name).is_file())
        metadata = json.loads((path / "metadata.json").read_text(encoding="utf-8-sig")) if not missing else {}
        validation = json.loads((path / "validation.json").read_text(encoding="utf-8-sig")) if not missing else {}
        ok = not missing and validation.get("status") == "PASS" and metadata.get("message_type") == "quadrotor_msgs/PolynomialTrajectory" and metadata.get("segment_count") == segments and metadata.get("git_commit") == MAIN_MERGE and metadata.get("am_planner_commit") == AM_PLANNER_COMMIT
        require(f"export_{label}", ok, {"missing": missing, "validation": validation.get("status"), "segment_count": metadata.get("segment_count")})
        export_checks[label] = ok
    variant = export_root / "grasp_waypoint_variant_01"
    variant_metadata = json.loads((variant / "metadata.json").read_text(encoding="utf-8-sig"))
    variant_validation = json.loads((variant / "validation.json").read_text(encoding="utf-8-sig"))
    require("waypoint_variant", variant_validation.get("status") == "PASS" and variant_metadata.get("message_type") == "quadrotor_msgs/PolynomialTrajectory")
    comparison = json.loads((root / "docs/evidence/S1-R2/waypoint_variant_comparison.json").read_text(encoding="utf-8-sig"))
    require("waypoint_values", comparison.get("baseline") == "data/trajectories/S1-R2/grasp_official" and comparison.get("variant") == "data/trajectories/S1-R2/grasp_waypoint_variant_01")
    require("waypoint_failures_preserved", (root / "docs/evidence/S1-R2/waypoint_variant/grasp_waypoint_variant_01_rosversion_fail").is_dir() and (root / "docs/evidence/S1-R2/waypoint_variant/grasp_waypoint_variant_01_wrapper_crlf_fail").is_dir())

    video_manifest = json.loads((root / "outputs/videos/S1-R2/video_manifest.json").read_text(encoding="utf-8-sig"))
    video_entries = video_manifest.get("entries", [])
    require("video_manifest", len(video_entries) == 4 and all(item.get("sha256") and item.get("bytes", 0) > 0 for item in video_entries))
    pngs = list((root / "outputs/figures/S1-R2").glob("*.png"))
    require("visualization_pngs", len(pngs) == 4 and all(path.stat().st_size < 2 * 1024 * 1024 for path in pngs), [path.name for path in pngs])
    repeat_validation = json.loads((export_root / "grasp_repeat/validation.json").read_text(encoding="utf-8-sig"))
    require("repeatability", repeat_validation.get("status") == "PASS")

    audit = json.loads((root / "docs/evidence/S1-R2/final_acceptance/s1_r2_trajectory_export_audit.json").read_text(encoding="utf-8-sig"))
    require("s1_r2_audit", not audit.get("errors") and not audit.get("warnings"))
    require("s1_r2_contract", (root / "docs/trajectory_contract.md").is_file() and (root / "docs/evidence/S1-R2/message_contract/message_definition.txt").is_file())

    diff = subprocess.run(["git", "diff", "--name-only", MAIN_MERGE, "HEAD", "--", "src"], cwd=root, capture_output=True, text=True, check=False)
    require("algorithm_boundary", diff.returncode == 0 and not diff.stdout.strip(), diff.stdout.strip())
    s0 = subprocess.run([sys.executable, "scripts/audit/check_s0_structure.py"], cwd=root, capture_output=True, text=True, check=False)
    require("global_s0_audit", s0.returncode == 0, s0.stdout[-2000:])

    require("state_s2_frozen", "S2：`IN_PROGRESS`" in progress_text and "S3--S8：`FROZEN`" in progress_text)
    result = {
        "decision": "PASS_WITH_LIMITATIONS" if not errors else "REVISION_REQUIRED_S1_FINAL_ACCEPTANCE",
        "errors": errors,
        "unresolved_warnings": [],
        "accepted_limitations": limitations,
        "checks": checks,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--update-record", action="store_true", help="explicitly update the historical tracked acceptance record")
    args = parser.parse_args()
    result = run()
    output = args.output
    if output is None and args.update_record:
        output = DEFAULT_OUTPUT
    if output is not None:
        resolved = output.resolve()
        if resolved == DEFAULT_OUTPUT.resolve() and not args.update_record:
            print(json.dumps({"decision": "OUTPUT_REFUSED", "errors": ["tracked_output_requires_update_record"]}, ensure_ascii=False))
            return 2
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "errors": result["errors"]}, ensure_ascii=False))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
