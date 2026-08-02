#!/usr/bin/env python3
"""Check whether the full three-task trajectory target was actually achieved."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "docs/evidence/S1-R1/runtime"
errors = []
for task, run in {"grasp": "grasp_cpu_checkpoint_run_02", "write": "write_cpu_checkpoint_run_01", "lift": "lift_cpu_checkpoint_run_01"}.items():
    path = RUNTIME / run / "numeric_validation.json"
    if not path.is_file():
        errors.append(f"{task}_evidence_missing")
        continue
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("success") is not True:
        errors.append(f"{task}_dual_trajectory_missing")
print(f"errors={len(errors)}")
print("warnings=0")
if errors:
    print("not_completed=" + ",".join(errors))
sys.exit(1 if errors else 0)
