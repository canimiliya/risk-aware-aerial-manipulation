#!/usr/bin/env python3
"""Audit S1-R1-R7 GPU rebuild evidence without turning a failed write into a pass."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


FIXED_COMMIT = "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha_manifest(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        rows[name.removeprefix("./")] = digest
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path("."))
    args = ap.parse_args()
    root = args.repo.resolve()
    ev = root / "docs/evidence/S1-R1/gpu_rebuild"
    errors: list[str] = []
    warnings: list[str] = []

    required = [
        "gpu_env_after_state.json", "gpu_env_final_pip_freeze.txt", "gpu_env_final_pip_check.txt",
        "gpu_source_commit.txt", "gpu_source_status.txt", "gpu_source_tree_sha256.txt",
        "build_summary.txt", "catkin_config.log", "cmake_python_extract.txt",
        "se3_node_readelf_dynamic.txt", "se3_node_ldd_runtime_final.txt", "se3_node_sha256.txt",
        "cpu_baseline_before/source_tracked_sha256.txt", "cpu_baseline_after/source_tracked_sha256.txt",
        "cpu_baseline_before/conda_explicit.txt", "cpu_baseline_after/conda_explicit.txt",
        "cpu_baseline_before/pip_freeze.txt", "cpu_baseline_after/pip_freeze.txt",
        "write_gpu_run_01_retry_11/roslaunch.log", "write_gpu_run_01_retry_11/rosnode_list.txt",
        "write_gpu_run_01_retry_11/trajectory_type.txt", "write_gpu_run_01_retry_11/trajectory_arm_type.txt",
    ]
    for name in required:
        if not (ev / name).exists():
            errors.append(f"missing evidence: {name}")

    def read(name: str) -> str:
        try:
            return (ev / name).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    try:
        gpu_state = json.loads(read("gpu_env_after_state.json"))
    except json.JSONDecodeError as exc:
        gpu_state = {}
        errors.append(f"invalid gpu state: {exc}")

    if gpu_state.get("python", "").find("3.9.23") < 0:
        errors.append("GPU Python is not 3.9.23")
    if gpu_state.get("torch") != "2.7.1+cu128":
        errors.append("GPU Torch is not 2.7.1+cu128")
    if gpu_state.get("cuda_available") is not True or gpu_state.get("capability") != [12, 0]:
        errors.append("RTX 5060 Ti CUDA hard gate failed")
    if "No broken requirements found." not in read("gpu_env_final_pip_check.txt"):
        errors.append("GPU pip check failed")
    for dep in ("numpy", "autodiff", "pybind11", "empy", "catkin_pkg", "PyYAML", "netifaces"):
        if not re.search(rf"(?im)^{re.escape(dep)}(?:\s|==|\s@)", read("gpu_env_final_pip_freeze.txt")):
            errors.append(f"missing GPU build/runtime dependency: {dep}")

    if FIXED_COMMIT not in read("gpu_source_commit.txt"):
        errors.append("GPU source commit drift")
    if read("gpu_source_status.txt").strip():
        errors.append("GPU source tree is dirty")
    if "All 19 packages succeeded" not in read("build_summary.txt"):
        errors.append("Catkin build is not 19/19")
    cmake = read("cmake_python_extract.txt")
    if 'version "3.9.23"' not in cmake or "libpython3.9.so" not in cmake:
        errors.append("CMake did not configure Python 3.9")
    readelf = read("se3_node_readelf_dynamic.txt")
    if "libpython3.9.so.1.0" not in readelf:
        errors.append("GPU se3_node does not link libpython3.9")
    if "libpython3.8.so.1.0" in readelf:
        errors.append("GPU se3_node also links libpython3.8; ABI gate is not clean")
    if "not found" in read("se3_node_ldd_runtime_final.txt"):
        errors.append("GPU se3_node has unresolved runtime libraries")

    before = canonical_sha_manifest(ev / "cpu_baseline_before/source_tracked_sha256.txt")
    after = canonical_sha_manifest(ev / "cpu_baseline_after/source_tracked_sha256.txt")
    if before != after:
        extra = sorted(set(after) - set(before))
        missing = sorted(set(before) - set(after))
        changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
        # Catkin can materialize the tracked top-level symlink after the first
        # snapshot; it is not a source edit. Common tracked files must match.
        if changed:
            errors.append("CPU tracked-source SHA changed: " + ",".join(changed[:10]))
        if extra == ["src/uam_sim/delta-display/CMakeLists.txt"] and not missing:
            warnings.append("CPU manifest gained the catkin top-level symlink after the first snapshot; common source hashes still match")
        else:
            errors.append("CPU tracked-source manifest membership changed")
    for name in ("conda_explicit.txt", "pip_freeze.txt", "source_commit.txt", "source_status.txt", "se3_node_sha256.txt"):
        if sha(ev / f"cpu_baseline_before/{name}") != sha(ev / f"cpu_baseline_after/{name}"):
            errors.append(f"CPU baseline changed: {name}")

    runtime = read("write_gpu_run_01_retry_11/roslaunch.log")
    write_ok = all(token in runtime for token in ("Using device: cuda", "JPS", "MINCO"))
    if "failed to get the Python codec" in runtime:
        errors.append("write stopped before se3_node initialization: Python codec/ABI error")
    elif not write_ok:
        errors.append("write has no complete GPU execution evidence")
    if not (ev / "write_gpu_run_01_retry_11/trajectory_type.txt").read_text(encoding="utf-8", errors="replace").strip():
        warnings.append("write did not publish a trajectory")
    if not (ev / "grasp_gpu_run_01").exists() and not (ev / "lift_gpu_run_01").exists():
        warnings.append("grasp/lift were correctly not run because write did not pass")

    # Inspect only files introduced in this change for forbidden artifacts.
    changed = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=root, text=True, capture_output=True, check=False).stdout.splitlines()
    changed += subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, text=True, capture_output=True, check=False).stdout.splitlines()
    forbidden = []
    for name in sorted(set(changed)):
        path = root / name
        try:
            if path.is_file() and (path.suffix.lower() in {".whl", ".vhdx", ".appx"} or path.stat().st_size > 10 * 1024 * 1024):
                forbidden.append(name)
        except OSError:
            warnings.append(f"unreadable link skipped during artifact scan: {name}")
    if forbidden:
        errors.append("forbidden large/binary files: " + ",".join(forbidden[:20]))

    result = {
        "errors": errors,
        "warnings": warnings,
        "decision": "BLOCKED_S1_R1_GPU_PYTHON_ABI" if any("libpython3.8" in e for e in errors) else ("REVISION_REQUIRED" if errors else "SUBMITTED_S1_R1_GPU_OFFICIAL_BASIC_REPRO"),
        "build": "19/19" if "All 19 packages succeeded" in read("build_summary.txt") else "not-pass",
        "write": "blocked_before_trajectory" if not write_ok else "evidence-present",
        "grasp_lift_run": False,
        "forbidden_files": forbidden,
    }
    (ev / "gpu_rebuild_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = ["# S1-R1 GPU 平行重建审计", "", f"decision={result['decision']}", f"errors={len(errors)} warnings={len(warnings)}", "", "## 错误"]
    md += [f"- {item}" for item in errors] or ["- 无"]
    md += ["", "## 警告"]
    md += [f"- {item}" for item in warnings] or ["- 无"]
    (ev / "gpu_rebuild_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
