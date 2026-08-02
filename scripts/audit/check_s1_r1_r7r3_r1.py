#!/usr/bin/env python3
"""Read-only audit for the R7-R3-R1 Python 3.9/GPU trajectory acceptance."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


FIXED_AM_COMMIT = "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d"
EXPECTED_HEAD = "5b12ec829b826392675ab732c53cda96b7550ad7"
SUCCESSFUL_RUNS = {
    "write": "write_r7r3_r1_gpu_run_02",
    "grasp": "grasp_r7r3_r1_gpu_run_02",
    "lift": "lift_r7r3_r1_gpu_run_01",
    "grasp_repeat": "grasp_r7r3_r1_gpu_run_03",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def load_json(path: Path) -> dict:
    try:
        return json.loads(read_text(path))
    except (json.JSONDecodeError, OSError):
        return {}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    state = root / "docs/evidence/S1-R1/r7r3_r1_state_gate"
    overlay = root / "docs/evidence/S1-R1/r7r3_r1_ros_overlay"
    integration = root / "docs/evidence/S1-R1/r7r3_r1_integration"
    runtime = root / "docs/evidence/S1-R1/r7r3_r1_runtime"
    errors: list[str] = []
    warnings: list[str] = []

    def check(name: str, condition: bool, message: str) -> None:
        (passed := checks).__setitem__(name, bool(condition))
        if not condition:
            errors.append(message)

    checks: dict[str, bool] = {}
    coord = root / ".coordination/S1-R1-R7-R2"
    check("coordination_present", coord.is_dir(), ".coordination was deleted")
    tracked = subprocess.run(
        ["git", "ls-files", ".coordination"], cwd=root, text=True, capture_output=True, check=False
    ).stdout.strip()
    check("coordination_untracked", not tracked, ".coordination is tracked")
    exclude = read_text(root / ".git/info/exclude")
    check("local_exclude", "/.coordination/" in exclude, "local .coordination exclusion is missing")
    check("start_head", EXPECTED_HEAD == subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False
    ).stdout.strip(), "HEAD drifted before the authorized change")

    inventory = load_json(state / "coordination_inventory.json")
    check("coordination_inventory", inventory.get("file_count") == 19 and inventory.get("tracked") is False,
          "coordination inventory does not preserve the 19-file untracked state")
    lock = load_json(overlay / "source_lock.json")
    check("official_overlay_lock", len(lock.get("repositories", [])) == 2 and all(r.get("commit") for r in lock["repositories"]),
          "official ROS overlay source lock is incomplete")
    graph = load_json(integration / "full_python_abi_graph.json")
    check("full_abi_python39", graph.get("python38_occurrence_count") == 0 and graph.get("not_found_count") == 0,
          "full ABI graph contains Python 3.8 or unresolved runtime libraries")
    check("am_commit", FIXED_AM_COMMIT in read_text(integration / "source_status_after.txt"),
          "AM-Planner fixed commit is missing")
    patch = read_text(integration / "am_planner.patch")
    patch_files = [line[6:] for line in patch.splitlines() if line.startswith("--- a/")]
    check("only_two_cmake_files", len(patch_files) == 2 and sorted(patch_files) == ["src/plan/plan_manage/CMakeLists.txt", "src/plan/traj_opt/CMakeLists.txt"],
          "AM-Planner patch does not contain exactly the two authorized CMake files")
    check("patch_hash", sha256(integration / "am_planner.patch") == read_text(integration / "patch_sha256.txt").split()[0],
          "AM-Planner patch SHA256 mismatch")
    build = read_text(integration / "build_attempt_02.log")
    check("nineteen_packages", "Found 19 packages" in build and "Failed: No packages failed" in build and "Abandoned: No packages were abandoned" in build,
          "19-package build evidence is incomplete")
    if "Warnings: 8 packages succeeded with warnings" in build:
        warnings.append("Catkin reports 8 warning-bearing packages; this is not the card's errors=0,warnings=0 target.")

    probe = read_text(integration / "interpreter_probe_normal.log") + read_text(integration / "interpreter_probe_env_i.log")
    check("interpreter_gpu_probe", "3.9.23" in probe and "2.7.1+cu128" in probe and "torch.cuda.is_available=True" in probe and "RTX 5060 Ti" in probe,
          "embedded interpreter/GPU probe is incomplete")

    run_results: dict[str, dict] = {}
    for label, run_id in SUCCESSFUL_RUNS.items():
        run = runtime / run_id
        summary = load_json(run / "result_summary.json")
        validation = load_json(run / "numeric_validation.json")
        launch = read_text(run / "roslaunch.log")
        run_results[label] = {"run_id": run_id, "summary": summary, "validation": validation}
        check(f"{label}_capture", summary.get("capture_exit") == 0 and validation.get("success") is True,
              f"{label} capture/numeric validation failed")
        check(f"{label}_cuda", "Using device: cuda" in launch and "initialized on cuda" in launch,
              f"{label} lacks in-process CUDA evidence")
        check(f"{label}_topics", "/trajectory" in validation.get("received_topics", []) and "/trajectory_arm" in validation.get("received_topics", []),
              f"{label} did not capture both trajectory topics")
        for topic in ("/trajectory", "/trajectory_arm"):
            item = validation.get(topic, {})
            check(f"{label}_{topic}_finite", item.get("nan_count") == 0 and item.get("inf_count") == 0 and item.get("nonzero_numeric_fields", 0) > 0 and item.get("positive_numeric_fields", 0) > 0,
                  f"{label} {topic} numeric gate failed")
        check(f"{label}_no_codec", "failed to get the Python codec" not in launch and "segmentation fault" not in launch.lower(),
              f"{label} contains a codec or segmentation failure")
        check(f"{label}_required_files", all((run / name).exists() for name in ("command.txt", "environment.txt", "processes.json", "roslaunch.log", "trajectory.json", "trajectory_arm.json", "numeric_validation.json", "cleanup_log.txt", "overlay_paths.txt", "source_status_after.txt")),
              f"{label} is missing required runtime evidence")

    write_launch = read_text(runtime / SUCCESSFUL_RUNS["write"] / "roslaunch.log")
    for token in ("JPS search path!", "MINCO setup successfully!", "Finish optimization!"):
        check(f"write_{token}", token in write_launch, f"write missing required marker: {token}")
    write_monitor = load_json(runtime / SUCCESSFUL_RUNS["write"] / "monitor_summary.json")
    check("write_monitor_summary", write_monitor.get("sample_count", 0) > 0 and write_monitor.get("gpu_utilization_percent_max", 0) > 0,
          "write monitor summary is missing")
    if not write_monitor.get("se3_gpu_pid_seen"):
        warnings.append("nvidia-smi exposed the se3 PID but returned [Not Found] for its process name; CUDA use is supported by the in-process log and GPU utilization samples.")
    if "No logs to publish!" in write_launch:
        warnings.append("AM-Planner emitted the non-fatal '[MANAGE]: No logs to publish!' message after publishing the trajectory.")

    check("grasp_repeatability", (runtime / "grasp_repeatability_comparison.json").exists(), "grasp repeatability comparison is missing")
    stash = subprocess.run(["git", "stash", "list"], cwd=root, text=True, capture_output=True, check=False).stdout
    check("stash_preserved", "stash@{0}" in stash and "stash@{1}" in stash, "stash@{0}/stash@{1} evidence is missing")
    forbidden: list[str] = []
    changed = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, text=True, capture_output=True, check=False).stdout.splitlines()
    changed += subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=root, text=True, capture_output=True, check=False).stdout.splitlines()
    for name in sorted(set(changed)):
        path = root / name
        if path.is_file() and path.stat().st_size > 10 * 1024 * 1024:
            forbidden.append(name)
    check("no_large_files", not forbidden, "files over 10 MB would be submitted: " + ",".join(forbidden))
    diff_check = subprocess.run(["git", "diff", "--check"], cwd=root, text=True, capture_output=True, check=False)
    check("git_diff_check", diff_check.returncode == 0, "git diff --check failed")

    result = {
        "decision": "SUBMITTED_R7R3_GPU_OFFICIAL_BASIC_REPRO" if not errors else "REVISION_REQUIRED",
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "successful_runs": run_results,
        "forbidden_large_files": forbidden,
        "status_policy": {"S1-R1": "SUBMITTED_FOR_REVIEW", "S1": "IN_PROGRESS", "S2-S8": "FROZEN"},
        "note": "This audit deliberately keeps non-fatal runtime/build warnings visible; it does not convert the review submission into PASS.",
    }
    out = state / "r7r3_r1_audit.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
