from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_COMMIT = "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d"
RUNTIME_RUNS = {
    "smoke_free": "smoke_free_run_08",
    "loose": "loose_run_01",
    "nominal": "nominal_run_01",
    "nominal_repeat": "nominal_repeat_01",
}


def run(root: Path = ROOT) -> dict[str, object]:
    required = [
        root / "docs/evidence/S2-R2/environment/environment_setup_attempt.md",
        root / "docs/evidence/S2-R2/environment/source_clone_provenance.json",
        root / "docs/evidence/S2-R2/build/build_gate.md",
        root / "docs/evidence/S2-R2/abi/abi_gate.md",
        root / "docs/evidence/S2-R2/planner_contract/task_schema.md",
        root / "docs/evidence/S2-R2/planner_contract/supported_waypoint_constraints.md",
        root / "docs/evidence/S2-R2/planner_contract/inter_info_contract.json",
        root / "docs/evidence/S2-R2/planner_contract/map_contract.md",
        root / "docs/evidence/S2-R2/planner_contract/state_vector_contract.md",
        root / "docs/evidence/S2-R2/planner_contract/trajectory_output_contract.md",
        root / "docs/evidence/S2-R2/planner_contract/unavailable_features.md",
        root / "docs/evidence/S2-R2/final_acceptance/s2_r2_am_planner_audit.json",
        root / "docs/evidence/S2-R2/validation/real_run_validation.json",
        root / "docs/milestones/S2_R2_status.md",
        root / "docs/reports/S2-R2_am_planner_crossarm_planning_report.md",
        root / "docs/evidence/S2-R2/maps/smoke_free.json",
        root / "docs/evidence/S2-R2/maps/loose.json",
        root / "docs/evidence/S2-R2/maps/nominal.json",
        root / "docs/evidence/S2-R2/maps/narrow.json",
    ]
    errors: list[str] = []
    checks: dict[str, object] = {}

    def require(name: str, value: bool, detail: object | None = None) -> None:
        checks[name] = value if detail is None else {"ok": value, "detail": detail}
        if not value:
            errors.append(name)

    require("required_evidence", all(p.is_file() and p.stat().st_size > 0 for p in required))
    source = root / "third_party/am-planner"
    source_head = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip()
    require("official_commit", source_head == OFFICIAL_COMMIT, source_head)

    inter_info = json.loads((root / "docs/evidence/S2-R2/planner_contract/inter_info_contract.json").read_text(encoding="utf-8"))
    require("inter_info_contract", inter_info.get("source_commit") == OFFICIAL_COMMIT and [m.get("expected_size") for m in inter_info.get("modes", [])] == [4, 7, 17, 20])
    require("q3_not_task_input", inter_info.get("vector_convention", {}).get("q3_input") is False)

    audit = json.loads((root / "docs/evidence/S2-R2/final_acceptance/s2_r2_am_planner_audit.json").read_text(encoding="utf-8"))
    require("corrected_audit", audit.get("decision") == "SUBMITTED_S2_R2_AM_PLANNER_READY")
    require("contract_correction_label", audit.get("contract_correction_label") == "REVISED_S2_R2_PLANNER_CONTRACT")
    require("algorithm_boundary", audit.get("checks", {}).get("algorithm_source_modified") is False)
    require("system_boundary", audit.get("checks", {}).get("system_ros_modified") is False and audit.get("checks", {}).get("conda_modified") is False)
    require("no_forbidden_conversion", audit.get("checks", {}).get("forbidden_cpu_or_weight_conversion") is False)
    provenance = json.loads((root / "docs/evidence/S2-R2/environment/source_clone_provenance.json").read_text(encoding="utf-8"))
    require("source_clone_provenance", provenance.get("selected_source_clone", {}).get("head") == OFFICIAL_COMMIT and provenance.get("new_workspace", {}).get("head") == OFFICIAL_COMMIT and provenance.get("new_workspace", {}).get("clean_before_patch") is True)

    validation = json.loads((root / "docs/evidence/S2-R2/validation/real_run_validation.json").read_text(encoding="utf-8"))
    for variant, run_id in RUNTIME_RUNS.items():
        run_dir = root / "docs/evidence/S2-R2/runtime" / run_id
        processes = json.loads((run_dir / "processes.json").read_text(encoding="utf-8"))
        numeric = json.loads((run_dir / "numeric_validation.json").read_text(encoding="utf-8"))
        require(f"{variant}_capture_exit", processes.get("capture_exit") == 0)
        require(f"{variant}_dual_topics", set(numeric.get("received_topics", [])) == {"/trajectory", "/trajectory_arm"})
        require(f"{variant}_finite", numeric.get("/trajectory", {}).get("nan_count") == 0 and numeric.get("/trajectory", {}).get("inf_count") == 0 and numeric.get("/trajectory_arm", {}).get("nan_count") == 0 and numeric.get("/trajectory_arm", {}).get("inf_count") == 0)
        result = validation["variants"][variant]
        require(f"{variant}_three_rates", set(result.get("frequencies", {})) == {"100Hz", "200Hz", "400Hz"})
        require(f"{variant}_dynamic_base", result["frequencies"]["100Hz"]["base"]["path_length_m"] > 0.1)
        require(f"{variant}_dynamic_arm_cartesian", result["frequencies"]["100Hz"]["arm_cartesian"]["path_length_m"] > 0.01)
        require(f"{variant}_end_effector_world_reconstructed", result["frequencies"]["100Hz"]["end_effector_world"]["finite"] is True)
        require(f"{variant}_proxy_clearance", result["frequencies"]["100Hz"]["proxy_clearance"]["gated_min_clearance_m"] >= 0.010)
        require(f"{variant}_direction_equivalent", result.get("direction_constraint", {}).get("status") == "EQUIVALENT_HORIZONTAL_DIRECTION_CONSTRAINT" and result["direction_constraint"].get("jps_endpoint_error_max_m") <= 1e-9 and result["direction_constraint"].get("jps_horizontal_direction_error_max_deg") <= 1e-9)
        require(f"{variant}_threshold_sensitivity", set(result["frequencies"]["100Hz"]["proxy_clearance"].get("threshold_sensitivity", {})) == {"0.02m", "0.05m", "0.10m"})

    repeat = validation.get("nominal_repeat", {})
    require("nominal_repeat_contract", repeat.get("contract_match") is True)
    require("nominal_repeat_endpoints", max(repeat.get("base_start_abs_delta_m", 1.0), repeat.get("base_end_abs_delta_m", 1.0), repeat.get("arm_start_abs_delta_m", 1.0), repeat.get("arm_end_abs_delta_m", 1.0), repeat.get("end_effector_start_abs_delta_m", 1.0), repeat.get("end_effector_end_abs_delta_m", 1.0), repeat.get("nominal_gated_min_clearance_abs_delta_m", 1.0)) <= 1e-9)
    status = (root / "docs/milestones/S2_R2_status.md").read_text(encoding="utf-8")
    require("submitted_status", "SUBMITTED_FOR_REVIEW" in status and "S2-R2" in status and "S3-S8" in status)

    return {"decision": "SUBMITTED_S2_R2_AM_PLANNER_READY" if not errors else "REVISION_REQUIRED", "errors": errors, "warnings": [], "unresolved_warnings": [], "checks": checks, "official_commit": source_head}


def main() -> int:
    result = run()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
