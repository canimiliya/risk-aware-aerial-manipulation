from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_COMMIT = "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d"


def run(root: Path = ROOT) -> dict[str, object]:
    required = [
        root / "docs/evidence/S2-R2/environment/environment_setup_attempt.md",
        root / "docs/evidence/S2-R2/build/build_gate.md",
        root / "docs/evidence/S2-R2/abi/abi_gate.md",
        root / "docs/evidence/S2-R2/planner_contract/task_schema.md",
        root / "docs/evidence/S2-R2/planner_contract/supported_waypoint_constraints.md",
        root / "docs/evidence/S2-R2/planner_contract/map_contract.md",
        root / "docs/evidence/S2-R2/planner_contract/state_vector_contract.md",
        root / "docs/evidence/S2-R2/planner_contract/trajectory_output_contract.md",
        root / "docs/evidence/S2-R2/planner_contract/unavailable_features.md",
        root / "docs/evidence/S2-R2/final_acceptance/s2_r2_am_planner_audit.json",
        root / "docs/milestones/S2_R2_status.md",
        root / "docs/reports/S2-R2_am_planner_crossarm_planning_report.md",
    ]
    errors: list[str] = []
    checks: dict[str, object] = {}

    def require(name: str, value: bool) -> None:
        checks[name] = value
        if not value:
            errors.append(name)

    require("required_evidence", all(p.is_file() and p.stat().st_size > 0 for p in required))
    source = root / "third_party/am-planner"
    source_head = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    require("official_commit", source_head == OFFICIAL_COMMIT)
    contract = json.loads(
        (root / "docs/evidence/S2-R2/final_acceptance/s2_r2_am_planner_audit.json").read_text(encoding="utf-8")
    )
    require("contract_block_recorded", contract.get("decision") == "BLOCKED_S2_R2_PLANNER_CONTRACT")
    require("delta_joint_contract_absent", contract.get("checks", {}).get("delta_three_joint_input_supported") is False)
    require("joint_base_inter_contract_absent", contract.get("checks", {}).get("dynamic_base_plus_delta_q_plus_inter_points") is False)
    require("runtime_not_fabricated", contract.get("checks", {}).get("runtime_attempted") is False)
    require("no_ros_dual_trajectory_claim", contract.get("checks", {}).get("ros_dual_trajectory_captured") is False)
    require("algorithm_boundary", contract.get("checks", {}).get("algorithm_source_modified") is False)
    require("status_document", "BLOCKED_S2_R2_PLANNER_CONTRACT" in (root / "docs/milestones/S2_R2_status.md").read_text(encoding="utf-8"))

    return {
        "decision": "BLOCKED_S2_R2_PLANNER_CONTRACT" if not errors else "REVISION_REQUIRED",
        "errors": errors,
        "warnings": [],
        "unresolved_warnings": [],
        "checks": checks,
        "blocking_reason": contract.get("blocking_reason"),
    }


def main() -> int:
    result = run()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
