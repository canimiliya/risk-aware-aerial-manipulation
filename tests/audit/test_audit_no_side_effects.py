from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_historical_audits_leave_status_and_acceptance_bytes_unchanged() -> None:
    historical = [
        ROOT / "docs/evidence/S1/final_acceptance/s1_final_acceptance.json",
        ROOT / "docs/evidence/S2-R0/final_acceptance/s2_r0_workspace_preflight_audit.json",
        ROOT / "docs/evidence/S2-R0/final_acceptance/s2_r0_final_acceptance.json",
        ROOT / "docs/evidence/S2-R1/final_acceptance/s2_r1_continuous_planning_audit.json",
        ROOT / "docs/evidence/S2-R4/final_acceptance/s2_r4_execution_feasible_audit.json",
        ROOT / "docs/evidence/S2-R5/s2_r5_audit.json",
        ROOT / "docs/evidence/S2-R6/s2_r6_audit.json",
    ]
    before_status = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT, text=True)
    before = {path: digest(path) for path in historical}
    commands = [
        [sys.executable, "scripts/audit/check_s1_final_acceptance.py"],
        [sys.executable, "scripts/audit/check_s2_r0_workspace_preflight.py"],
        [sys.executable, "scripts/audit/check_s2_r0_final_acceptance.py"],
        [sys.executable, "scripts/audit/check_s2_r1_continuous_planning.py"],
        [sys.executable, "scripts/audit/check_s2_r4_execution_feasible.py"],
        [sys.executable, "scripts/audit/check_s2_r5_adaptive_constraints.py"],
        [sys.executable, "scripts/audit/check_s2_r6_execution_envelope.py"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
    assert subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT, text=True) == before_status
    assert {path: digest(path) for path in historical} == before
