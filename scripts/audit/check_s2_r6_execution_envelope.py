"""Strict S2-R6 evidence audit; historical records are read-only inputs."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "docs/evidence/S2-R6"
RUNTIME = EV / "runtime"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    required = [
        EV / "source_manifest.json",
        EV / "calibration.json",
        EV / "envelope/source_contract.md",
        EV / "envelope/anchor_balls.json",
        EV / "envelope/local_certification.json",
        EV / "envelope/corridor_connectivity.json",
        EV / "envelope/round1_coverage.json",
        EV / "envelope/envelope_manifest.json",
        EV / "envelope/visual_manifest.json",
        EV / "final_validation/candidate_summary.json",
        EV / "final_validation/frequency_convergence.json",
        EV / "final_validation/repeatability.json",
        EV / "final_validation/ablation.json",
        EV / "final_validation/formal_runs.json",
        ROOT / "third_party/patches/AM-Planner_S2-R6_execution_envelope.patch",
        ROOT / "third_party/patches/AM-Planner_S2-R6_execution_envelope.sha256",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"missing {path.relative_to(ROOT)}")

    manifest = read(EV / "source_manifest.json") if (EV / "source_manifest.json").exists() else {}
    patch = ROOT / "third_party/patches/AM-Planner_S2-R6_execution_envelope.patch"
    sha_file = ROOT / "third_party/patches/AM-Planner_S2-R6_execution_envelope.sha256"
    if patch.exists() and sha_file.exists():
        actual = hashlib.sha256(patch.read_bytes()).hexdigest()
        recorded = sha_file.read_text(encoding="utf-8").split()[0]
        if actual != recorded or actual != manifest.get("patch_sha256"):
            errors.append("patch SHA256 mismatch")
        patch_text = patch.read_text(encoding="utf-8", errors="replace")
        changed_paths = [line.split(" b/", 1)[1] for line in patch_text.splitlines() if line.startswith("diff --git a/") and " b/" in line]
        forbidden_paths = ("se3gcopter.h", "minco_base.h", "plan_manage.cpp", "urdf", "xacro")
        if any(any(token in path.lower() for token in forbidden_paths) for path in changed_paths):
            errors.append("patch touches a forbidden source path")
        if "third_party/am-planner" in subprocess.run(["git", "diff", "--name-only", "--", "third_party/am-planner"], cwd=ROOT, capture_output=True, text=True, check=False).stdout:
            errors.append("tracked third_party/am-planner worktree changed")

    envelope = read(EV / "envelope/envelope_manifest.json")
    balls = read(EV / "envelope/anchor_balls.json")
    local = read(EV / "envelope/local_certification.json")
    connectivity = read(EV / "envelope/corridor_connectivity.json")
    coverage = read(EV / "envelope/round1_coverage.json")
    if balls.get("count") not in range(12, 97) or envelope.get("anchor_count") != balls.get("count"):
        errors.append("anchor count is outside 12..96 or inconsistent")
    if balls.get("radius_m") != 0.0015:
        errors.append("anchor radius drift")
    sampling = envelope.get("workspace_sampling", {})
    for key, expected in (("random_fk_sample_count", 1_000_000), ("random_fk_valid_count", 1_000_000), ("corner_count", 8), ("corner_fk_valid_count", 8)):
        if sampling.get(key) != expected:
            errors.append(f"workspace sampling {key} != {expected}")
    if sampling.get("boundary_layer_sample_count", 0) <= 0 or sampling.get("boundary_fk_valid_count") != sampling.get("boundary_layer_sample_count"):
        errors.append("boundary-layer validation incomplete")
    if not local.get("all_balls_hard_branch_pass") or any(not x.get("hard_branch_pass") or x.get("nonfinite_ik_count") for x in local.get("certifications", [])):
        errors.append("local ball certification failed")
    if not connectivity.get("all_adjacent_balls_overlap") or coverage.get("round1_fixed_points_within_anchor_balls") is not True or not coverage.get("interpolated_corridor_g_nonnegative"):
        errors.append("corridor coverage/connectivity failed")
    if not coverage.get("raw_round1_polynomial_is_not_claimed_covered"):
        errors.append("raw violating polynomial was incorrectly relabeled")

    disabled_cfg = (EV / "configs/s2_r6_disabled.yaml").read_text(encoding="utf-8")
    if "UseExecutionEnvelopeBarrier: false" not in disabled_cfg:
        errors.append("disabled configuration is not disabled")
    calibration = read(EV / "calibration.json")
    if set(calibration.get("weight_candidates", {})) != {"w0", "10w0", "100w0"} or calibration.get("selection_rule", "").find("first candidate") < 0:
        errors.append("weight calibration candidates incomplete")

    runs = [p for p in RUNTIME.iterdir() if p.is_dir()]
    expected_runs = {"round1_disabled", "nominal_w0", "nominal_10w0", "nominal_100w0", "smoke_final_100w0", "loose_final_100w0", "nominal_repeat_final_100w0", "narrow_final_100w0"}
    if {p.name for p in runs} != expected_runs:
        errors.append("runtime candidate set incomplete")
    for run in sorted(runs, key=lambda p: p.name):
        process = run / "processes.json"
        numeric = run / "numeric_validation.json"
        validation = run / "validation_multirate.json"
        if not process.exists() or read(process).get("capture_exit") != 0:
            errors.append(f"capture failed: {run.name}")
        if not numeric.exists():
            errors.append(f"numeric validation missing: {run.name}")
        else:
            data = read(numeric)
            if not data.get("success") or data.get("received_topics") != ["/trajectory", "/trajectory_arm"]:
                errors.append(f"topic contract failed: {run.name}")
            for topic in ("/trajectory", "/trajectory_arm"):
                if data.get(topic, {}).get("nan_count") != 0 or data.get(topic, {}).get("inf_count") != 0:
                    errors.append(f"NaN/Inf present: {run.name}/{topic}")
        if not validation.exists():
            errors.append(f"multirate validation missing: {run.name}")

    candidates = read(EV / "final_validation/candidate_summary.json")
    if candidates.get("w0", {}).get("nominal_hard_gate_pass") or candidates.get("10w0", {}).get("nominal_hard_gate_pass"):
        errors.append("a failing low-weight candidate was marked passing")
    if not candidates.get("100w0", {}).get("nominal_hard_gate_pass"):
        errors.append("100w0 did not pass nominal hard gates")
    formal = read(EV / "final_validation/formal_runs.json")
    if not all(v.get("capture_exit") == 0 and v.get("nominal_hard_gate_pass") and v.get("direction_pass") for v in formal.values()):
        errors.append("formal smoke/loose/repeat/narrow acceptance failed")
    freq = read(EV / "final_validation/frequency_convergence.json")
    if set(freq) != {"100", "200", "400", "800", "2000"} or not all(freq[k].get("finite") and freq[k].get("joint_gate_pass") and freq[k].get("full_body_gate_pass") for k in freq):
        errors.append("multirate convergence contract failed")
    repeat = read(EV / "final_validation/repeatability.json")
    if not repeat.get("gate_both_pass") or repeat.get("max_abs_arm_position_delta_m", 1.0) > 1e-12:
        errors.append("repeatability failed")

    figures = EV / "envelope/figures"
    visual_manifest = read(EV / "envelope/visual_manifest.json")
    if len(list(figures.glob("*.png"))) < 8 or len(list(figures.glob("*.gif"))) < 2:
        errors.append("visual acceptance incomplete")
    if len(visual_manifest.get("png", [])) < 8 or len(visual_manifest.get("local_animation", [])) < 2:
        errors.append("visual manifest incomplete")

    result = {
        "decision": "PASS" if not errors and not warnings else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "algorithm_source_diff": False,
        "scope": "S2-R6 continuous Cartesian execution-envelope barrier only",
        "stage_status": "SUBMITTED_FOR_REVIEW",
    }
    (EV / "s2_r6_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "errors": len(errors), "warnings": len(warnings)}, ensure_ascii=False))
    return 0 if not errors and not warnings else 1


if __name__ == "__main__":
    raise SystemExit(main())
