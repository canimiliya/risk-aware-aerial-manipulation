#!/usr/bin/env python3
"""Audit the recorded CPU-Torch dependency gate and the truthful runtime result."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/evidence/S1-R1"
STATUS = ROOT / "docs/milestones/S1_R1_status.md"

def load(relative):
    path = EVIDENCE / relative
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

torch = load("torch_runtime/torch_probe.json")
weight = load("torch_runtime/workspace_weight_load_probe.json")
grasp = load("runtime/grasp_torch_run_01_retry_03/numeric_validation.json")
errors = []
if not torch or not str(torch.get("torch_version", "")).startswith("2.4.1"):
    errors.append("torch_version")
if not torch or torch.get("cuda_available") is not False or torch.get("cuda_version") is not None:
    errors.append("cpu_mode")
if not torch or not torch.get("nn_forward_ok") or not torch.get("autograd_ok"):
    errors.append("torch_nn_autograd")
if not weight or not weight.get("all_finite") or weight.get("tensor_count", 0) <= 0:
    errors.append("workspace_weight")
for name in ("torchvision", "torchaudio", "triton"):
    if name not in (EVIDENCE / "torch_runtime/forbidden_packages_probe.txt").read_text(encoding="utf-8", errors="replace"):
        errors.append(f"forbidden_probe_{name}")
if not (EVIDENCE / "build_after_torch/build_after_torch.log").read_text(encoding="utf-8", errors="replace").count("All 19 packages succeeded"):
    errors.append("build_19_of_19")
if not grasp or grasp.get("success") is not False or grasp.get("received_topics") != []:
    errors.append("grasp_blocker_evidence")
if "SUBMITTED_FOR_REVIEW" not in STATUS.read_text(encoding="utf-8", errors="replace"):
    errors.append("truthful_status")

print(f"errors={len(errors)}")
print("warnings=1" if not errors else "warnings=0")
print("runtime_status=TORCH_AND_BUILD_OK_GRASP_ABORT_NO_TRAJECTORY" if not errors else "missing=" + ",".join(errors))
sys.exit(1 if errors else 0)
