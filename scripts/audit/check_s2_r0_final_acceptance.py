from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run(root: Path = ROOT) -> dict[str, object]:
    errors: list[str] = []
    checks: dict[str, object] = {}

    def require(label: str, ok: bool, detail: object = None) -> None:
        checks[label] = detail if detail is not None else ok
        if not ok:
            errors.append(label)

    branch = subprocess.run(["git", "branch", "--show-current"], cwd=root, capture_output=True, text=True, check=False).stdout.strip()
    require("s2_branch", branch in {
        "agent/s2-r0-delta-workspace-scene-contract",
        "main",
        "agent/s2-r2-am-planner-crossarm-planning",
    }, branch)
    preflight = subprocess.run(["python", "scripts/audit/check_s2_r0_workspace_preflight.py"], cwd=root, capture_output=True, text=True, check=False)
    require("r0_preflight", preflight.returncode == 0, preflight.stdout[-1000:])
    required = [
        root / "docs/evidence/S2-R0/final_acceptance/s2_r0_workspace_preflight_audit.json",
        root / "docs/evidence/S2-R0/g_arm_preflight.json",
        root / "docs/reports/S2-R0_delta_workspace_preflight_report.md",
        root / "docs/milestones/S2_R0_status.md",
    ]
    require("required_artifacts", all(path.is_file() and path.stat().st_size > 0 for path in required), [str(path.relative_to(root)) for path in required if not path.is_file()])
    status = (root / "docs/milestones/S2_R0_status.md").read_text(encoding="utf-8-sig")
    require("final_status", "S2-R0：`PASS_WITH_LIMITATIONS`" in status and "S2：`IN_PROGRESS`" in status)
    garm = json.loads((root / "docs/evidence/S2-R0/g_arm_preflight.json").read_text(encoding="utf-8-sig"))
    require("g_arm_evidence", garm.get("decision") == "G_ARM_READY_FOR_FULL_PLANNING" and garm.get("errors") == [])
    result = {
        "decision": "PASS_WITH_LIMITATIONS" if not errors else "REVISION_REQUIRED",
        "errors": errors,
        "warnings": [
            "crossarm/obstacle/body/rotor/tool values remain PROVISIONAL_S2_ASSUMPTION",
            "S2-R0 is a static workspace preflight and not complete continuous planning",
        ],
        "checks": checks,
        "accepted_limitations": [
            "official Delta FK and joint/launch geometry are fixed; task-scene dimensions are provisional",
            "vehicle pose, tool pose/length, mesh collision, dynamics and flight-control coupling are unavailable",
        ],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("docs/evidence/S2-R0/final_acceptance/s2_r0_final_acceptance.json"))
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "errors": result["errors"], "warnings": result["warnings"]}, ensure_ascii=False))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
