from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MERGE_COMMITS = ("8df48d2b4edc0d219ad8eb3a9b211fb291daf2ab", "90ae58e6d65afc754437572eae1f3228fd522d42", "918cb8318a1b5867b3333caf820ba52a8cdd67d1")


def run(root: Path = ROOT) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}

    def check(name: str, value: bool) -> None:
        checks[name] = value
        if not value:
            errors.append(name)

    def load(path: str) -> dict[str, object]:
        return json.loads((root / path).read_text(encoding="utf-8"))

    acceptance = load("docs/evidence/S2/final_acceptance/s2_final_acceptance.json")
    readiness = load("docs/evidence/S2/final_readiness/s2_final_readiness.json")
    status = (root / "docs/milestones/S2_status.md").read_text(encoding="utf-8")
    check("acceptance_decision", acceptance.get("decision") == "PASS_S2_WITH_LIMITATIONS")
    check("acceptance_errors_empty", acceptance.get("errors") == [])
    check("acceptance_warnings_empty", acceptance.get("unresolved_warnings") == [])
    check("readiness_decision", readiness.get("decision") == "READY_FOR_S2_FINAL_REVIEW")
    check("readiness_errors_empty", readiness.get("errors") == [])
    check("readiness_warnings_empty", readiness.get("unresolved_warnings") == [])
    check("readiness_hard_checks", all(v is True for v in readiness.get("checks", {}).values()))
    check("status_consistent", "S2：`PASS_WITH_LIMITATIONS`" in status and "S3：`NOT_STARTED`" in status and "S4--S8：`FROZEN`" in status)
    check("patch_reproducible", acceptance.get("audit", {}).get("s2_r6_patch_reproducible") is True and readiness.get("checks", {}).get("s2_r6_patch_reproducible") is True)
    check("historical_side_effect_free", acceptance.get("audit", {}).get("side_effect_free") is True and readiness.get("checks", {}).get("audit_side_effects_absent") is True)
    check("nominal_evidence", all((root / p).is_file() for p in ("docs/evidence/S2-R6/runtime/nominal_100w0/trajectory.json", "docs/evidence/S2-R6/runtime/nominal_repeat_final_100w0/trajectory.json")))
    repo = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root, capture_output=True, text=True, check=False)
    check("git_repository", repo.returncode == 0 and repo.stdout.strip() == "true")
    ancestor_checks = {}
    for commit in MERGE_COMMITS:
        result = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=root, check=False)
        ancestor_checks[commit] = result.returncode == 0
    check("s2_merge_ancestry", all(ancestor_checks.values()))
    return {"decision": "PASS" if not errors else "REVISION_REQUIRED", "errors": errors, "warnings": warnings, "authoritative_s2_closed": not errors, "original_audits_required": False, "checks": checks, "merge_ancestry": ancestor_checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(payload, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
