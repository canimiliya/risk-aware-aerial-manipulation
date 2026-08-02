#!/usr/bin/env python3
"""Audit the complete S1-R1-R6-R1 official CUDA dependency recovery gate."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path("."))
    args = ap.parse_args()
    root = args.repo.resolve()
    ev = root / "docs/evidence/S1-R1/gpu_dependency_recovery"
    errors, warnings = [], []
    required = [
        "torch_metadata.txt", "gpu_runtime_lock.txt", "gpu_runtime_lock.json", "gpu_runtime_lock_sha256.txt",
        "official_wheel_manifest.json", "official_wheel_manifest.md", "wheel_inventory_before.json", "wheel_inventory_before.md",
        "wheel_inventory_after.json", "wheelhouse_verification.md", "gpu_torch_probe.json", "gpu_checkpoint_probe.json",
        "gpu_model_validation.json", "workspace_model_cpu_benchmark.json", "workspace_model_gpu_benchmark.json",
        "cpu_gpu_benchmark_comparison.json", "cpu_gpu_benchmark_comparison.md", "gpu_path_decision.json", "gpu_path_decision.md",
        "cpu_env_r6_after.txt", "cpu_env_r6_after_sha256.txt", "gpu_env_r6_after.txt", "source_r6_after.txt",
    ]
    for name in required:
        if not (ev / name).exists(): errors.append(f"missing evidence: {name}")
    try:
        lock = [x for x in (ev / "gpu_runtime_lock.txt").read_text(encoding="utf-8").splitlines() if x.strip()]
        lock_json = load(ev / "gpu_runtime_lock.json")
        if len(lock) != 21 or lock_json.get("expected_dependency_drift") != []: errors.append("METADATA lock count/drift gate failed")
        manifest = load(ev / "official_wheel_manifest.json")
        if len(manifest.get("rows", [])) != 21 or manifest.get("failures"): errors.append("official wheel manifest incomplete")
        wheel_after = load(ev / "wheel_inventory_after.json")
        if any(wheel_after.get(k) not in (0, []) for k in ("missing", "corrupt_or_mismatch", "unknown")): errors.append("wheelhouse verification failed")
        torch = load(ev / "gpu_torch_probe.json")
        if not torch.get("hard_gate_pass"): errors.append("Torch/RTX hard gate failed")
        if torch.get("warnings"): errors.append("Torch probe emitted warnings")
        for key, row in torch.get("steps", {}).items():
            if not row.get("success") or not all(row.get(k, True) for k in ("finite", "finite_loss", "finite_grad")): errors.append(f"Torch step failed: {key}")
        checkpoint = load(ev / "gpu_checkpoint_probe.json")
        model = load(ev / "gpu_model_validation.json")
        if not checkpoint.get("hard_gate_pass") or not model.get("strict_load") or not model.get("forward") or not model.get("autograd"): errors.append("checkpoint/model hard gate failed")
        bench = load(ev / "cpu_gpu_benchmark_comparison.json")
        speedups = {str(row["batch"]): row["forward_autograd"]["speedup_x"] for row in bench.get("rows", [])}
        if float(speedups.get("576", 0)) < 3 or float(speedups.get("960", 0)) < 3: errors.append("key batch autograd speedup below 3x")
        decision = load(ev / "gpu_path_decision.json")
        if decision.get("decision") != "GPU_REBUILD_RECOMMENDED": errors.append("unexpected GPU route decision")
        cpu_text = (ev / "cpu_env_r6_after.txt").read_text(encoding="utf-8-sig")
        if "torch==2.4.1+cpu" not in cpu_text or "2.4.1+cpu\nFalse" not in cpu_text: errors.append("CPU baseline drift")
        old_hash = (root / "docs/evidence/S1-R1/gpu_preflight/cpu_env_after_sha256.txt").read_text().strip().lower()
        new_hash = (ev / "cpu_env_r6_after_sha256.txt").read_text().strip().lower()
        if old_hash != new_hash: errors.append("CPU environment SHA changed")
        source = (ev / "source_r6_after.txt").read_text(encoding="utf-8-sig")
        if "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d" not in source or "git status --short" in source: errors.append("source state drift or capture marker leaked")
        if "TARGET SOURCE" not in source or "bind" in source.lower(): errors.append("weight mount boundary failed")
        gpu_env = (ev / "gpu_env_r6_after.txt").read_text(encoding="utf-8-sig")
        if "No broken requirements found." not in gpu_env: errors.append("pip check did not pass")
    except Exception as exc:
        errors.append(f"audit exception: {type(exc).__name__}: {exc}")
    result = {"errors": errors, "warnings": warnings, "required_count": len(required), "decision": "GPU_REBUILD_RECOMMENDED" if not errors else "REVISION_REQUIRED", "torch_hard_gate": None, "checkpoint_hard_gate": None}
    try:
        result["torch_hard_gate"] = bool(load(ev / "gpu_torch_probe.json").get("hard_gate_pass"))
        result["checkpoint_hard_gate"] = bool(load(ev / "gpu_checkpoint_probe.json").get("hard_gate_pass"))
        result["benchmark_rows"] = len(load(ev / "cpu_gpu_benchmark_comparison.json").get("rows", []))
    except Exception:
        pass
    (ev / "gpu_dependency_recovery_audit.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (ev / "gpu_dependency_recovery_audit.md").write_text("# GPU dependency recovery audit\n\n" + "```json\n" + json.dumps(result, indent=2, ensure_ascii=False) + "\n```\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
