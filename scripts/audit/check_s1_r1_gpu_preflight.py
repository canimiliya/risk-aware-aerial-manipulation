#!/usr/bin/env python3
"""Audit the bounded R6 GPU preflight evidence and scope boundaries."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--repo", default="."); args = ap.parse_args()
    root = Path(args.repo).resolve(); ev = root / "docs/evidence/S1-R1/gpu_preflight"; errors=[]; warnings=[]
    required = ["wsl_gpu_baseline.txt", "nvidia_smi_query.csv", "dev_dxg_probe.txt", "cpu_env_before.txt", "cpu_env_before_sha256.txt", "cpu_env_after.txt", "cpu_env_after_sha256.txt", "gpu_torch_probe.json", "gpu_checkpoint_probe.json", "gpu_model_validation.json", "workspace_model_gpu_benchmark.json", "cpu_gpu_benchmark_comparison.json", "gpu_path_decision.json"]
    for name in required:
        if not (ev/name).exists(): errors.append(f"missing:{name}")
    if (ev/"cpu_env_before.txt").exists() and (ev/"cpu_env_after.txt").exists() and sha(ev/"cpu_env_before.txt") != sha(ev/"cpu_env_after.txt"): errors.append("CPU environment evidence hash changed")
    def load(name):
        try: return json.loads((ev/name).read_text(encoding="utf-8"))
        except Exception as exc: errors.append(f"invalid:{name}:{exc}"); return {}
    torch = load("gpu_torch_probe.json"); ck = load("gpu_checkpoint_probe.json"); model = load("gpu_model_validation.json"); bench=load("cpu_gpu_benchmark_comparison.json"); decision=load("gpu_path_decision.json")
    if decision.get("decision") != "REVISION_REQUIRED":
        if not torch.get("hard_gate_pass"): errors.append("GPU hard gate failed")
        if torch.get("capability") != [12,0] or torch.get("device_name") != "NVIDIA GeForce RTX 5060 Ti": errors.append("wrong GPU identity/capability")
        if not ck.get("hard_gate_pass"): errors.append("checkpoint gate failed")
        if not all(model.get(k) is True for k in ("strict_load","forward","autograd")): errors.append("model validation failed")
    else:
        if torch.get("status") != "BLOCKED_BEFORE_KERNEL_PROBE": errors.append("revision status lacks explicit kernel blocker")
        if ck.get("status") != "NOT_RUN_DEPENDENCY_BLOCKED" or model.get("status") != "NOT_RUN_DEPENDENCY_BLOCKED": errors.append("revision status lacks explicit not-run evidence")
    rows=bench.get("rows",[])
    if decision.get("decision") != "REVISION_REQUIRED" and [r.get("batch") for r in rows] != [1,96,192,576,960]: errors.append("benchmark batches incomplete")
    if decision.get("decision") not in {"GPU_REBUILD_RECOMMENDED","GPU_REBUILD_FEASIBLE_BUT_UNCERTAIN","GPU_PATH_NOT_FEASIBLE","REVISION_REQUIRED"}: errors.append("invalid route decision")
    forbidden=[]
    # Only inspect files introduced by this R6 change; historical third-party
    # and runtime evidence may legitimately contain large binaries/logs.
    import subprocess
    changed = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=root, text=True, capture_output=True, check=False).stdout.splitlines()
    changed += subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, text=True, capture_output=True, check=False).stdout.splitlines()
    for name in sorted(set(changed)):
        p=root/name
        if p.is_file() and (p.suffix.lower() in {".whl", ".vhdx", ".appx"} or p.stat().st_size > 10*1024*1024): forbidden.append(name)
    if forbidden: errors.append("forbidden large/binary files: " + ",".join(forbidden[:20]))
    result={"errors":errors,"warnings":warnings,"required_count":len(required),"decision":decision.get("decision"),"torch_hard_gate":torch.get("hard_gate_pass"),"checkpoint_hard_gate":ck.get("hard_gate_pass"),"benchmark_rows":len(rows)}
    (ev/"gpu_preflight_audit.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    lines=["# GPU 预检自动审计","",f"errors={len(errors)} warnings={len(warnings)}",""]
    lines += [f"- {e}" for e in errors] or ["- 无错误"]
    (ev/"gpu_preflight_audit.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2)); return 1 if errors else 0


if __name__ == "__main__": raise SystemExit(main())
