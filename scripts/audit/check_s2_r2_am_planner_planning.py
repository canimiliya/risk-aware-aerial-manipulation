from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_COMMIT = "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d"
RUNTIME_RUNS = {"smoke_free": "smoke_free_run_08", "loose": "loose_run_01", "nominal": "nominal_run_01", "nominal_repeat": "nominal_repeat_01"}


def _git_head(source: Path) -> str | None:
    if not source.is_dir() or not (source / ".git").exists():
        return None
    result = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return result.stdout.strip() or None


def run(root: Path = ROOT, audit_mode: str = "archival", source_clone: Path | None = None) -> dict[str, object]:
    required = [
        "docs/evidence/S2-R2/environment/environment_setup_attempt.md", "docs/evidence/S2-R2/environment/source_clone_provenance.json",
        "docs/evidence/S2-R2/build/build_gate.md", "docs/evidence/S2-R2/abi/abi_gate.md",
        "docs/evidence/S2-R2/planner_contract/task_schema.md", "docs/evidence/S2-R2/planner_contract/supported_waypoint_constraints.md",
        "docs/evidence/S2-R2/planner_contract/inter_info_contract.json", "docs/evidence/S2-R2/planner_contract/map_contract.md",
        "docs/evidence/S2-R2/planner_contract/state_vector_contract.md", "docs/evidence/S2-R2/planner_contract/trajectory_output_contract.md",
        "docs/evidence/S2-R2/planner_contract/unavailable_features.md", "docs/evidence/S2-R2/final_acceptance/s2_r2_am_planner_audit.json",
        "docs/evidence/S2-R2/validation/real_run_validation.json", "docs/milestones/S2_R2_status.md",
        "docs/reports/S2-R2_am_planner_crossarm_planning_report.md", "docs/evidence/S2-R2/maps/smoke_free.json",
        "docs/evidence/S2-R2/maps/loose.json", "docs/evidence/S2-R2/maps/nominal.json", "docs/evidence/S2-R2/maps/narrow.json",
    ]
    errors: list[str] = []
    checks: dict[str, object] = {}

    def require(name: str, value: bool, detail: object | None = None) -> None:
        checks[name] = value if detail is None else {"ok": value, "detail": detail}
        if not value:
            errors.append(name)

    require("required_evidence", all((root / p).is_file() and (root / p).stat().st_size > 0 for p in required))
    provenance = json.loads((root / "docs/evidence/S2-R2/environment/source_clone_provenance.json").read_text(encoding="utf-8"))
    inter_info = json.loads((root / "docs/evidence/S2-R2/planner_contract/inter_info_contract.json").read_text(encoding="utf-8"))
    audit = json.loads((root / "docs/evidence/S2-R2/final_acceptance/s2_r2_am_planner_audit.json").read_text(encoding="utf-8"))
    validation = json.loads((root / "docs/evidence/S2-R2/validation/real_run_validation.json").read_text(encoding="utf-8"))

    if audit_mode == "original":
        clone = source_clone or (root / "third_party/am-planner")
        source_head = _git_head(clone)
        require("official_source_clone_missing", source_head is not None, str(clone))
        require("official_commit", source_head == OFFICIAL_COMMIT, source_head)
        official_commit_source = "local_source_clone"
        local_clone_checked = True
    else:
        source_head = None
        require("committed_provenance", provenance.get("official_commit") == OFFICIAL_COMMIT, provenance.get("official_commit"))
        require("selected_provenance", provenance.get("selected_source_clone", {}).get("head") == OFFICIAL_COMMIT)
        require("new_workspace_provenance", provenance.get("new_workspace", {}).get("head") == OFFICIAL_COMMIT and provenance.get("new_workspace", {}).get("clean_before_patch") is True)
        official_commit_source = "committed_provenance"
        local_clone_checked = False

    require("inter_info_contract", inter_info.get("source_commit") == OFFICIAL_COMMIT and [m.get("expected_size") for m in inter_info.get("modes", [])] == [4, 7, 17, 20])
    require("q3_not_task_input", inter_info.get("vector_convention", {}).get("q3_input") is False)
    require("corrected_audit", audit.get("decision") == "SUBMITTED_S2_R2_AM_PLANNER_READY")
    require("contract_correction_label", audit.get("contract_correction_label") == "REVISED_S2_R2_PLANNER_CONTRACT")
    require("algorithm_boundary", audit.get("checks", {}).get("algorithm_source_modified") is False)
    require("system_boundary", audit.get("checks", {}).get("system_ros_modified") is False and audit.get("checks", {}).get("conda_modified") is False)
    require("no_forbidden_conversion", audit.get("checks", {}).get("forbidden_cpu_or_weight_conversion") is False)

    for variant, run_id in RUNTIME_RUNS.items():
        run_dir = root / "docs/evidence/S2-R2/runtime" / run_id
        processes = json.loads((run_dir / "processes.json").read_text(encoding="utf-8"))
        numeric = json.loads((run_dir / "numeric_validation.json").read_text(encoding="utf-8"))
        require(f"{variant}_capture_exit", processes.get("capture_exit") == 0)
        require(f"{variant}_dual_topics", set(numeric.get("received_topics", [])) == {"/trajectory", "/trajectory_arm"})
        require(f"{variant}_finite", all(numeric.get(topic, {}).get("nan_count") == 0 and numeric.get(topic, {}).get("inf_count") == 0 for topic in ("/trajectory", "/trajectory_arm")))
        result = validation["variants"][variant]
        require(f"{variant}_three_rates", set(result.get("frequencies", {})) == {"100Hz", "200Hz", "400Hz"})
        require(f"{variant}_dynamic_base", result["frequencies"]["100Hz"]["base"]["path_length_m"] > 0.1)
        require(f"{variant}_dynamic_arm_cartesian", result["frequencies"]["100Hz"]["arm_cartesian"]["path_length_m"] > 0.01)
        require(f"{variant}_end_effector_world_reconstructed", result["frequencies"]["100Hz"]["end_effector_world"]["finite"] is True)
        require(f"{variant}_proxy_clearance", result["frequencies"]["100Hz"]["proxy_clearance"]["gated_min_clearance_m"] >= 0.010)
        require(f"{variant}_direction_equivalent", result.get("direction_constraint", {}).get("status") == "EQUIVALENT_HORIZONTAL_DIRECTION_CONSTRAINT")

    repeat = validation.get("nominal_repeat", {})
    require("nominal_repeat_contract", repeat.get("contract_match") is True)
    status = (root / "docs/milestones/S2_R2_status.md").read_text(encoding="utf-8")
    require("submitted_status", "SUBMITTED_FOR_REVIEW" in status and "S2-R2" in status and "S3-S8" in status)
    return {"decision": "SUBMITTED_S2_R2_AM_PLANNER_READY" if not errors else "REVISION_REQUIRED", "errors": errors, "warnings": [], "unresolved_warnings": [], "checks": checks, "official_commit": source_head, "official_commit_source": official_commit_source, "local_clone_checked": local_clone_checked, "audit_mode": audit_mode}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-mode", choices=("original", "archival"), default="archival")
    parser.add_argument("--source-clone", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(audit_mode=args.audit_mode, source_clone=args.source_clone)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(payload, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
