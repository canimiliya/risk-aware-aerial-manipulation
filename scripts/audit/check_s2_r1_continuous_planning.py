from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
R0_HEAD = "5564f5d407c75dfd9c776d5e43917c9f96c48702"


def run(root: Path = ROOT) -> dict[str, object]:
    errors: list[str] = []
    checks: dict[str, object] = {}

    def require(label: str, ok: bool, detail: object = None) -> None:
        checks[label] = detail if detail is not None else ok
        if not ok:
            errors.append(label)

    required = [
        root / "configs/planner/s2_r1_continuous_planning.yaml",
        root / "docs/evidence/S2-R1/continuous_full_body_plan.json",
        root / "docs/evidence/S2-R1/continuous_planning_manifest.json",
        root / "docs/reports/S2-R1_continuous_full_body_planning_report.md",
        root / "docs/milestones/S2_R1_status.md",
        root / "outputs/figures/S2-R1/continuous_full_body_plan.png",
    ]
    require("required_artifacts", all(path.is_file() and path.stat().st_size > 0 for path in required), [str(path.relative_to(root)) for path in required if not path.is_file()])
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=root, capture_output=True, text=True, check=False).stdout.strip()
    require("s2_branch", branch in {
        "agent/s2-r0-delta-workspace-scene-contract",
        "main",
        "agent/s2-r2-am-planner-crossarm-planning",
    }, branch)
    require("r0_base_present", subprocess.run(["git", "cat-file", "-e", f"{R0_HEAD}^{{commit}}"], cwd=root, capture_output=True, text=True, check=False).returncode == 0)
    require("algorithm_boundary", not subprocess.run(["git", "diff", "--name-only", f"{R0_HEAD}..HEAD", "--", "src"], cwd=root, capture_output=True, text=True, check=False).stdout.strip())

    config = (root / "configs/planner/s2_r1_continuous_planning.yaml").read_text(encoding="utf-8-sig")
    require("provisional_boundary", "PROVISIONAL_S2_R1_GATE" in config and "FIXED_WB_REFERENCE_PROVISIONAL" in config)
    plan = json.loads((root / "docs/evidence/S2-R1/continuous_full_body_plan.json").read_text(encoding="utf-8-sig"))
    require("planner_contract", plan.get("planner_contract") == "S2-R1_CONTINUOUS_KINEMATIC_PREPLANNING")
    require("waypoint_contract", plan.get("waypoint_names") == ["P0", "P1", "P2", "P3", "P4", "P5", "P6"])
    require("sample_contract", plan.get("sample_count") == 601 and plan.get("samples_per_segment") == 101)
    require("vehicle_state_contract", plan.get("vehicle_state_mode") == "FIXED_WB_REFERENCE_PROVISIONAL" and all(item.get("vehicle_pose_WB") == [0.0] * 6 for item in plan.get("samples", [])))
    metrics = plan.get("metrics", {})
    require("continuous_finite", plan.get("invalid_sample_count") == 0 and all(item.get("finite") is True for item in plan.get("samples", [])))
    require("continuous_nominal_gate", metrics.get("min_clearance_m", -1.0) >= 0.010 and metrics.get("min_joint_margin", -1.0) >= 0.10)
    require("jacobian_metrics", metrics.get("min_jacobian_min_singular_value", -1.0) > 0.0 and metrics.get("max_jacobian_condition_number", float("inf")) < 100.0)
    require("trajectory_figure", (root / "outputs/figures/S2-R1/continuous_full_body_plan.png").stat().st_size < 2 * 1024 * 1024)
    r0 = subprocess.run(["python", "scripts/audit/check_s2_r0_workspace_preflight.py"], cwd=root, capture_output=True, text=True, check=False)
    require("r0_audit", r0.returncode == 0, r0.stdout[-1000:])
    result = {
        "decision": "PASS_WITH_LIMITATIONS" if not errors else "REVISION_REQUIRED",
        "errors": errors,
        "warnings": [],
        "unresolved_warnings": [],
        "accepted_limitations": [
            "W->B remains a fixed zero reference, not a dynamic vehicle trajectory",
            "vehicle dynamics and flight-control constraints are not modeled",
            "tool length and complete 6D tool pose are not verified",
            "collision checks use provisional proxy geometry, not exact meshes",
            "this is not AM-Planner optimization or ROS PolynomialTrajectory evidence",
            "this is not complete S2 acceptance",
        ],
        "checks": checks,
        "metrics": metrics,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("docs/evidence/S2-R1/final_acceptance/s2_r1_continuous_planning_audit.json"))
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "errors": result["errors"], "warnings": result["warnings"]}, ensure_ascii=False))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
