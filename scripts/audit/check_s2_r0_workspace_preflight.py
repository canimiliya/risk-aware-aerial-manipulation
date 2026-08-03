from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs/evidence/S2-R0/final_acceptance/s2_r0_workspace_preflight_audit.json"
DEFAULT_MODE = "archival"
AM_PLANNER_COMMIT = "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d"
SUMMARY_PATH = Path("outputs/workspace/S2-R0/delta_workspace_100k.json")
NPZ_PATH = Path("outputs/workspace/S2-R0/delta_workspace_100k.npz")
SOURCE_PREFLIGHT_PATH = Path("docs/evidence/S2-R0/final_acceptance/s2_r0_workspace_preflight_audit.json")
FINAL_ACCEPTANCE_PATH = Path("docs/evidence/S2-R0/final_acceptance/s2_r0_final_acceptance.json")
RECOVERY_PATH = Path("docs/evidence/S2-R0/archive_recovery/workspace_summary_recovery.json")


def branch_is_allowed(branch: str, expected_branch: str | None = None) -> bool:
    """Allow a named branch, optionally enforcing the original exact branch."""
    return bool(branch) and (expected_branch is None or branch == expected_branch)


def git_stdout(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False).stdout.strip()


def read_json(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return None


def expected_summary(audit: dict[str, object] | None) -> dict[str, object] | None:
    if not audit:
        return None
    checks = audit.get("checks")
    return checks.get("workspace_summary") if isinstance(checks, dict) and isinstance(checks.get("workspace_summary"), dict) else None


def run(root: Path = ROOT, expected_branch: str | None = None, audit_mode: str = DEFAULT_MODE) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    limitations: list[str] = []
    checks: dict[str, object] = {"audit_mode": audit_mode}

    def require(label: str, ok: bool, detail: object = None) -> None:
        checks[label] = detail if detail is not None else ok
        if not ok:
            errors.append(label)

    if audit_mode not in {"original", "archival"}:
        return {"decision": "REVISION_REQUIRED", "errors": ["invalid_audit_mode"], "warnings": [], "checks": checks}

    required = [
        root / "docs/evidence/S2-R0/robot_model/source_inventory.md",
        root / "docs/evidence/S2-R0/robot_model/model_files.json",
        root / "docs/evidence/S2-R0/robot_model/frame_tree.md",
        root / "docs/evidence/S2-R0/robot_model/joint_contract.json",
        root / "docs/evidence/S2-R0/robot_model/geometry_contract.json",
        root / "docs/evidence/S2-R0/robot_model/collision_proxy_contract.json",
        root / "docs/evidence/S2-R0/robot_model/unavailable_parameters.md",
        root / "docs/coordinate_frame_contract.md",
        root / "configs/scene/s2_crossarm_nominal.yaml",
        root / "configs/robot/s2_delta_arm.yaml",
        root / "configs/planner/s2_workspace_gate.yaml",
        root / "docs/evidence/S2-R0/workspace_sampling_manifest.json",
        root / "docs/evidence/S2-R0/g_arm_preflight.json",
        root / "docs/reports/S2-R0_delta_workspace_preflight_report.md",
        root / "docs/milestones/S2_R0_status.md",
        root / SOURCE_PREFLIGHT_PATH,
        root / FINAL_ACCEPTANCE_PATH,
        root / SUMMARY_PATH,
    ]
    require("required_artifacts", all(path.is_file() and path.stat().st_size > 0 for path in required), [str(path.relative_to(root)) for path in required if not path.is_file()])

    branch = git_stdout(root, "branch", "--show-current")
    require("s2_branch", branch_is_allowed(branch, expected_branch), branch or "DETACHED_HEAD")
    if audit_mode == "archival":
        require("non_detached_head", bool(branch), branch or "DETACHED_HEAD")
    else:
        main_head = git_stdout(root, "rev-parse", "--verify", "refs/heads/main")
        merge_base = git_stdout(root, "merge-base", "HEAD", "main")
        require("base_main", bool(main_head) and merge_base == main_head, {"main": main_head, "merge_base": merge_base})
        base_for_diff = merge_base or main_head or "HEAD"
        require("algorithm_boundary", not git_stdout(root, "diff", "--name-only", f"{base_for_diff}..HEAD", "--", "src"))

    model = read_json(root / "docs/evidence/S2-R0/robot_model/model_files.json")
    joints = read_json(root / "docs/evidence/S2-R0/robot_model/joint_contract.json")
    geometry = read_json(root / "docs/evidence/S2-R0/robot_model/geometry_contract.json")
    require("official_model_commit", bool(model and joints) and model.get("am_planner_commit") == AM_PLANNER_COMMIT and joints.get("am_planner_commit") == AM_PLANNER_COMMIT)
    active_joints = joints.get("active_joints", []) if joints else []
    require("official_joint_contract", bool(joints) and joints.get("active_joint_order") == ["m1_1", "m2_1", "m3_1"] and all(item.get("lower_rad") == -1.57 and item.get("upper_rad") == 1.57 for item in active_joints if isinstance(item, dict)))
    require("official_geometry_contract", bool(geometry) and geometry.get("official_launch_values") == {"static_radius": 0.08, "moving_radius": 0.025, "upper_arm": 0.1, "lower_arm": 0.16, "scale": 1.0})

    config_text = read_text(root / "configs/scene/s2_crossarm_nominal.yaml") or ""
    require("provisional_scene_marked", "PROVISIONAL_S2_ASSUMPTION" in config_text)
    require("target_fake_declared", "target_fake:" in config_text and "target placeholder" in config_text)
    require("provisional_tool_marked", "PROVISIONAL_S2_ASSUMPTION" in (read_text(root / "configs/robot/s2_delta_arm.yaml") or ""))

    source_audit = read_json(root / SOURCE_PREFLIGHT_PATH)
    require("committed_preflight_audit", bool(source_audit) and source_audit.get("decision") == "SUBMITTED_S2_R0_G_ARM_READY" and source_audit.get("errors") == [])
    source_summary = expected_summary(source_audit)

    manifest = read_json(root / "docs/evidence/S2-R0/workspace_sampling_manifest.json")
    source_manifest = source_audit.get("checks", {}).get("workspace_manifest") if source_audit and isinstance(source_audit.get("checks"), dict) else None
    require("workspace_manifest", bool(manifest and source_manifest and manifest == source_manifest), manifest or "MISSING")

    npz = root / NPZ_PATH
    if npz.is_file():
        actual_hash = hashlib.sha256(npz.read_bytes()).hexdigest().upper()
        npz_ok = bool(manifest and actual_hash == manifest.get("local_npz_sha256"))
        checks["local_npz_status"] = "PRESENT_HASH_MATCH" if npz_ok else "PRESENT_HASH_MISMATCH"
        require("local_npz_sha256", npz_ok, {"actual": actual_hash, "expected": manifest.get("local_npz_sha256") if manifest else None})
    else:
        checks["local_npz_status"] = "NOT_PRESENT_LOCAL_ONLY"
        if audit_mode == "original":
            require("local_npz_missing", False, "outputs/workspace/S2-R0/delta_workspace_100k.npz")
        else:
            limitations.append("local NPZ is local-only and not present; archival mode did not perform byte rehash")

    summary = read_json(root / SUMMARY_PATH)
    require("workspace_summary_missing", summary is not None, str(SUMMARY_PATH))
    require("workspace_summary", summary is not None and source_summary is not None and summary == source_summary, summary or "MISSING")

    if audit_mode == "archival":
        recovery = read_json(root / RECOVERY_PATH)
        require("summary_recovery_provenance", bool(recovery) and recovery.get("recovery_type") == "RECOVERED_FROM_COMMITTED_ACCEPTANCE_EVIDENCE" and recovery.get("not_recomputed") is True and recovery.get("not_from_local_npz") is True, recovery or "MISSING")
        if recovery:
            source_ref = recovery.get("source_ref")
            source_path = recovery.get("source_path")
            expected_blob = git_stdout(root, "rev-parse", f"{source_ref}:{source_path}") if isinstance(source_ref, str) and isinstance(source_path, str) else ""
            recovery_ok = (
                summary is not None
                and recovery.get("source_object_path") == "checks.workspace_summary"
                and recovery.get("source_blob_sha") == expected_blob
                and recovery.get("recovered_file") == str(SUMMARY_PATH).replace("\\", "/")
                and recovery.get("field_comparison", {}).get("report_jacobian_metrics") is True
                and recovery.get("recovered_file_sha256") == hashlib.sha256((root / SUMMARY_PATH).read_bytes()).hexdigest()
                and recovery.get("recovered_bytes") == (root / SUMMARY_PATH).stat().st_size
                and recovery.get("recovered_lines") == len((root / SUMMARY_PATH).read_text(encoding="utf-8-sig").splitlines())
            )
            require("summary_recovery_provenance_details", recovery_ok, recovery)

    pose_results = read_json(root / "outputs/workspace/S2-R0/task_pose_evaluation.json")
    if audit_mode == "original":
        require("pose_sensitivity", bool(pose_results) and pose_results.get("loose", {}).get("feasible_count") == 7 and pose_results.get("nominal", {}).get("feasible_count") == 7 and pose_results.get("narrow", {}).get("feasible_count") == 0)
        require("p0_p6", bool(pose_results) and all(len(result.get("poses", [])) == 7 and [item.get("pose") for item in result.get("poses", [])] == ["P0", "P1", "P2", "P3", "P4", "P5", "P6"] for result in pose_results.values()))
    else:
        historical_checks = source_audit.get("checks", {}) if source_audit else {}
        require("pose_sensitivity", historical_checks.get("pose_sensitivity") is True, "committed preflight audit")
        require("p0_p6", historical_checks.get("p0_p6") is True, "committed preflight audit")
        if pose_results is None:
            limitations.append("local pose evaluation JSON is unavailable; archival mode relies on the committed preflight audit")
    figure = root / "outputs/figures/S2-R0/delta_workspace.png"
    if audit_mode == "original":
        require("workspace_figure", figure.is_file() and figure.stat().st_size < 2 * 1024 * 1024)
    else:
        require("workspace_figure", source_audit is not None and source_audit.get("checks", {}).get("workspace_figure") is True, "committed preflight audit")
        if not figure.is_file():
            limitations.append("local workspace figure is unavailable; archival mode relies on the committed preflight audit")

    garm = read_json(root / "docs/evidence/S2-R0/g_arm_preflight.json")
    require("g_arm_decision", bool(garm) and garm.get("decision") in {"G_ARM_READY_FOR_FULL_PLANNING", "G_ARM_GEOMETRY_INCONCLUSIVE", "G_ARM_NOT_FEASIBLE_IN_TESTED_GEOMETRY"}, garm.get("decision") if garm else "MISSING")
    require("g_arm_errors", bool(garm) and garm.get("errors") == [])
    require("g_arm_summary_consistent", bool(garm and summary) and garm.get("workspace", {}).get("sample_count") == summary.get("sample_count") and garm.get("workspace", {}).get("valid_fk_count") == summary.get("valid_fk_count") and garm.get("workspace", {}).get("invalid_fk_count") == summary.get("invalid_fk_count") and garm.get("workspace", {}).get("random_seed") == summary.get("random_seed") and garm.get("workspace", {}).get("boundary_samples_included") is True and garm.get("workspace", {}).get("position_min_m") == summary.get("position_min_m") and garm.get("workspace", {}).get("position_max_m") == summary.get("position_max_m"))
    require("state_gate", bool(garm) and garm.get("state") == {"s2_r0": "SUBMITTED_FOR_REVIEW", "s2": "IN_PROGRESS", "s3_s8": "FROZEN"})
    status_text = read_text(root / "docs/milestones/S2_R0_status.md") or ""
    require("status_document", ("S2-R0：`SUBMITTED_FOR_REVIEW`" in status_text or "S2-R0：`PASS_WITH_LIMITATIONS`" in status_text) and "S2：`IN_PROGRESS`" in status_text and "S3–S8：`FROZEN`" in status_text)
    report_text = read_text(root / "docs/reports/S2-R0_delta_workspace_preflight_report.md") or ""
    require("report_data_consistent", all(token in report_text for token in ["100,000", "20260803", "90,205", "9,795", "9.016e-7", "401.50"]))

    final_audit = read_json(root / FINAL_ACCEPTANCE_PATH)
    require("committed_final_acceptance", bool(final_audit) and final_audit.get("decision") == "PASS_WITH_LIMITATIONS" and final_audit.get("errors") == [])

    s0 = subprocess.run([sys.executable, "scripts/audit/check_s0_structure.py"], cwd=root, capture_output=True, text=True, check=False)
    require("s0_audit", s0.returncode == 0, s0.stdout[-1000:])
    with tempfile.TemporaryDirectory(prefix="s2_r0_s1_audit_") as tmp:
        s1 = subprocess.run([sys.executable, "scripts/audit/check_s1_final_acceptance.py", "--output", str(Path(tmp) / "s1_final_acceptance.json")], cwd=root, capture_output=True, text=True, check=False)
    require("s1_audit", s1.returncode == 0, s1.stdout[-1000:])

    credential = re.compile(r"ghp_|github_pat_|AKIA|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY", re.I)
    scoped = [root / "configs", root / "planner_bridge/workspace", root / "docs/evidence/S2-R0", root / "docs/reports/S2-R0_delta_workspace_preflight_report.md"]
    hits = [str(path.relative_to(root)) for base in scoped for path in ([base] if base.is_file() else base.rglob("*")) if path.is_file() and path.stat().st_size < 2 * 1024 * 1024 and credential.search(path.read_text(encoding="utf-8", errors="ignore"))]
    require("credential_scan", not hits, hits)
    large = [str(path.relative_to(root)) for base in scoped for path in ([base] if base.is_file() else base.rglob("*")) if path.is_file() and path.stat().st_size > 10 * 1024 * 1024]
    require("large_file_scan", not large, large)

    result = {
        "decision": "SUBMITTED_S2_R0_G_ARM_READY" if not errors and garm and garm.get("decision") == "G_ARM_READY_FOR_FULL_PLANNING" else ("SUBMITTED_S2_R0_GEOMETRY_INCONCLUSIVE" if not errors else "REVISION_REQUIRED"),
        "errors": errors,
        "warnings": warnings,
        "accepted_limitations": limitations,
        "checks": checks,
        "g_arm_decision": garm.get("decision") if garm else None,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-mode", choices=["original", "archival"], default=DEFAULT_MODE)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--expected-branch", default=None)
    parser.add_argument("--update-record", action="store_true", help="explicitly update the historical tracked acceptance record")
    args = parser.parse_args()
    result = run(expected_branch=args.expected_branch, audit_mode=args.audit_mode)
    output = args.output
    if output is None and args.update_record:
        output = DEFAULT_OUTPUT
    if output is not None:
        if output.resolve() == DEFAULT_OUTPUT.resolve() and not args.update_record:
            print(json.dumps({"decision": "OUTPUT_REFUSED", "errors": ["tracked_output_requires_update_record"]}, ensure_ascii=False))
            return 2
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "errors": result["errors"], "warnings": result["warnings"]}, ensure_ascii=False))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
