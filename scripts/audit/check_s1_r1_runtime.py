#!/usr/bin/env python3
"""Verify that S1-R1 records the build and its documented runtime blocker."""
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "docs/evidence/S1-R1/build_final/build_runtime_gate.log"
RUNTIME = ROOT / "docs/evidence/S1-R1/runtime/s1-r1-runtime/grasp_run_01_retry_03/roslaunch.log"
STATUS = ROOT / "docs/milestones/S1_R1_status.md"

checks = {
    "build_19_of_19": (BUILD, "All 19 packages succeeded"),
    "runtime_torch_blocker": (RUNTIME, "No module named 'torch'"),
    "runtime_abort_recorded": (RUNTIME, "Failed to initialize workspace probability model"),
    "status_is_runtime_blocker": (STATUS, "SUBMITTED_S1_R1_BUILD_WITH_RUNTIME_BLOCKER"),
}

errors = []
for name, (path, expected) in checks.items():
    if not path.is_file() or expected not in path.read_text(encoding="utf-8", errors="replace"):
        errors.append(name)

print(f"errors={len(errors)}")
print("warnings=1" if not errors else "warnings=0")
if not errors:
    print("runtime_status=BLOCKED_BY_FORBIDDEN_TORCH_DEPENDENCY")
else:
    print("missing=" + ",".join(errors))
sys.exit(1 if errors else 0)
