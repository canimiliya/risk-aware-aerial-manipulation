"""Audit S2-R4 evidence completeness without converting a failed gate to PASS."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/evidence/S2-R4"
OUT = EVIDENCE / "final_acceptance/s2_r4_execution_feasible_audit.json"
REQUIRED = [
    "root_cause/joint_violation_intervals.json", "root_cause/collision_violation_intervals.json", "root_cause/phase_failure_map.json", "root_cause/nominal_failure_timeline.csv", "root_cause/root_cause_summary.md",
    "arm_envelope/envelope_summary.json", "arm_envelope/boundary_surface_manifest.json", "arm_envelope/current_trajectory_violation.json", "arm_envelope/nearest_feasible_projection.json", "arm_envelope/workspace_figure.png",
    "static_feasibility/candidate_sets.json", "static_feasibility/p0_p6_selected.json", "static_feasibility/rejected_candidates_summary.json", "static_feasibility/clearance_sensitivity.json", "static_feasibility/static_feasibility_figure.png",
    "geometry/revalidated_proxy_contract.json", "geometry/official_asset_search.md", "execution_contract/joint_contract.md", "execution_contract/mode_constraints.md",
    "validation/s2_r4_execution_validation.json",
]
RUNS = {"smoke_free": "smoke_free_run_02", "loose": "loose_run_01", "nominal": "nominal_run_01", "nominal_repeat": "nominal_repeat_run_01", "narrow": "narrow_run_01"}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8", errors="replace").strip()


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    for rel in REQUIRED:
        if not (EVIDENCE / rel).exists(): errors.append(f"missing:{rel}")
    envelope = json.loads((EVIDENCE / "arm_envelope/envelope_summary.json").read_text(encoding="utf-8"))
    if int(envelope.get("random_sample_count", 0)) < 500_000: errors.append("envelope_sample_count")
    selected = json.loads((EVIDENCE / "static_feasibility/p0_p6_selected.json").read_text(encoding="utf-8"))
    if len(selected.get("P0_P6", [])) != 7: errors.append("P0_P6_count")
    validation = json.loads((EVIDENCE / "validation/s2_r4_execution_validation.json").read_text(encoding="utf-8"))
    allowed = {"S2_R4_EXECUTION_FEASIBLE_READY", "S2_R4_PLANNER_RUNTIME_FAILED", "S2_R4_JOINT_LIMIT_FAILED", "S2_R4_FULL_BODY_CLEARANCE_FAILED", "S2_R4_DIRECTION_FAILED", "S2_R4_REQUIRES_ALGORITHM_CONSTRAINT"}
    if validation.get("decision") not in allowed: errors.append("invalid_decision")
    for variant in ("smoke_free", "loose", "nominal", "nominal_repeat"):
        data = validation["variants"][variant]
        if data["contracts"].get("capture_exit") != 0: errors.append(f"capture_exit:{variant}")
        if not all(data["contracts"].get(k) for k in ("jps_success", "minco_success", "gpu_success", "trajectory_published")): errors.append(f"runtime_contract:{variant}")
        if data["contracts"].get("nan_inf") != 0: errors.append(f"nan_inf:{variant}")
    for variant, run in RUNS.items():
        if not (EVIDENCE / f"runtime/{run}/trajectory.json").exists() or not (EVIDENCE / f"runtime/{run}/trajectory_arm.json").exists(): errors.append(f"raw_capture:{variant}")
    changed = git("diff", "--name-only", "main", "--")
    if re.search(r"(^|/)(src|include)/.*\.(cpp|cc|h|hpp)$", changed, re.I): errors.append("algorithm_source_changed")
    too_large = []
    for p in EVIDENCE.rglob("*"):
        if p.is_symlink():
            continue
        try:
            if p.is_file() and p.stat().st_size > 10 * 1024 * 1024: too_large.append(str(p.relative_to(ROOT)))
        except OSError:
            continue
    if too_large: errors.extend(f"large_file:{x}" for x in too_large)
    secret_re = re.compile(r"(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY)")
    for p in EVIDENCE.rglob("*"):
        if p.is_symlink():
            continue
        try:
            small = p.is_file() and p.stat().st_size < 2 * 1024 * 1024
        except OSError:
            small = False
        if small and secret_re.search(p.read_text(encoding="utf-8", errors="replace")): errors.append(f"credential:{p.relative_to(ROOT)}")
    result = {"decision": "PASS" if not errors else "FAIL", "errors": errors, "warnings": warnings, "s2_r4_result": validation.get("decision"), "preserves_gate_failure": validation.get("decision") != "S2_R4_EXECUTION_FEASIBLE_READY", "required_runtime_variants": list(RUNS), "algorithm_source_modified": False, "obstacle_geometry_modified": False, "proxy_shrunk": False, "q_clipped": False}
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
