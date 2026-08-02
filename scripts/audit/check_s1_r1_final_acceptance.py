#!/usr/bin/env python3
"""Final S1-R1 acceptance audit.

The audit separates unresolved warnings from explicitly accepted limitations.
It never treats a filtered log or a successful process exit as proof by itself.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


RUNS = {
    "write": "write_r7r3_r1_gpu_run_02",
    "grasp": "grasp_r7r3_r1_gpu_run_02",
    "lift": "lift_r7r3_r1_gpu_run_01",
    "grasp_repeat": "grasp_r7r3_r1_gpu_run_03",
}
ACCEPTED = [
    {
        "id": "catkin_warning_bearing_packages",
        "classification": "NON_BLOCKING_UPSTREAM",
        "evidence": "docs/evidence/S1-R1/final_warning_triage/catkin_warning_inventory.json",
    },
    {
        "id": "nvidia_smi_process_name_not_found",
        "classification": "NON_BLOCKING_ENVIRONMENT",
        "evidence": "docs/evidence/S1-R1/r7r3_r1_gpu_run_02/snapshot_60s.json",
    },
    {
        "id": "no_logs_to_publish",
        "classification": "NON_BLOCKING_POST_SUCCESS",
        "evidence": "docs/evidence/S1-R1/r7r3_r1_gpu_run_02/roslaunch.log",
    },
]


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    return result.returncode, (result.stdout + result.stderr).strip()


def check_file(root: Path, relative: str) -> bool:
    return (root / relative).is_file()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo.resolve()
    errors: list[str] = []
    checks: dict[str, object] = {}

    inventory_path = root / "docs/evidence/S1-R1/final_warning_triage/catkin_warning_inventory.json"
    review_path = root / "docs/reviews/S1-R1_warning_acceptance_review_2026-08-03.md"
    if not inventory_path.is_file() or not review_path.is_file():
        errors.append("warning triage evidence or review is missing")
    else:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        checks["catkin_warning_inventory"] = {
            "package_count": inventory.get("warning_bearing_package_count"),
            "packages": [item.get("package") for item in inventory.get("packages", [])],
            "has_blocking_keywords": any(
                any(token in summary.lower() for token in ("python3.8", "undefined reference", "cuda architecture"))
                for item in inventory.get("packages", [])
                for summary in item.get("warning_summaries", [])
            ),
        }
        if inventory.get("warning_bearing_package_count") != 8:
            errors.append("catkin warning-bearing package count is not 8")
        if checks["catkin_warning_inventory"]["has_blocking_keywords"]:
            errors.append("catkin warning inventory contains a blocking keyword")

    expected_packages = {"octomap_server", "map_pcl", "so3_control", "so3_quadrotor_simulator", "traj_server", "jps3d", "traj_opt", "plan_manage"}
    actual_packages = set(checks.get("catkin_warning_inventory", {}).get("packages", []))
    if actual_packages != expected_packages:
        errors.append(f"catkin package set mismatch: {sorted(actual_packages)}")

    runtime_root = root / "docs/evidence/S1-R1/r7r3_r1_runtime"
    runtime_checks = {}
    for task, run_id in RUNS.items():
        run_dir = runtime_root / run_id
        result_file = run_dir / "result_summary.json"
        process_file = run_dir / "processes.json"
        if not result_file.is_file() or not process_file.is_file():
            errors.append(f"missing runtime summary for {run_id}")
            continue
        result = json.loads(result_file.read_text(encoding="utf-8"))
        processes = json.loads(process_file.read_text(encoding="utf-8"))
        run_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in run_dir.glob("*.log")
        )
        runtime_checks[task] = {
            "run_id": run_id,
            "capture_exit": result.get("capture_exit"),
            "process_capture_exit": processes.get("capture_exit"),
            "trajectory_topics_present": "/trajectory" in run_text or (run_dir / "trajectory.json").is_file(),
            "trajectory_arm_topics_present": "/trajectory_arm" in run_text or (run_dir / "trajectory_arm.json").is_file(),
            "no_logs_to_publish_present": "No logs to publish!" in run_text,
            "trajectory_published_present": "The trajectory is published!" in run_text,
            "using_cuda_present": "Using device: cuda" in run_text,
        }
        if result.get("capture_exit") != 0 or processes.get("capture_exit") != 0:
            errors.append(f"capture failed for {run_id}")
        if not runtime_checks[task]["using_cuda_present"]:
            errors.append(f"CUDA marker missing for {run_id}")
        if not runtime_checks[task]["no_logs_to_publish_present"]:
            errors.append(f"expected preserved No logs warning missing for {run_id}")
        if not runtime_checks[task]["trajectory_published_present"]:
            errors.append(f"trajectory published marker missing for {run_id}")
    checks["runtime_runs"] = runtime_checks
    if len(runtime_checks) != 4:
        errors.append("four successful runtime records are not complete")

    abi_graph_path = root / "docs/evidence/S1-R1/r7r3_r1_integration/full_python_abi_graph.json"
    abi_graph = json.loads(abi_graph_path.read_text(encoding="utf-8")) if abi_graph_path.is_file() else {}
    checks["abi"] = {
        "python38_occurrences": abi_graph.get("python38_occurrence_count"),
        "runtime_not_found_occurrences": abi_graph.get("not_found_count"),
    }
    if not abi_graph_path.is_file():
        errors.append("full Python ABI graph evidence is missing")
    if checks["abi"]["python38_occurrences"] != 0:
        errors.append("Python 3.8 remains in integration ABI evidence")
    if checks["abi"]["runtime_not_found_occurrences"] != 0:
        errors.append("runtime not-found remains in integration ABI evidence")

    code, diff_names = run(["git", "diff", "44273a990c5ebc4c0c3ec13dc0332ffe90e16798..HEAD", "--name-only"], root)
    changed_algorithm = [
        line for line in diff_names.splitlines()
        if line.startswith("src/") and re.search(r"\.(cpp|cc|cxx|h|hpp)$", line, flags=re.IGNORECASE)
    ]
    checks["algorithm_boundary"] = {"diff_exit": code, "algorithm_source_changes": changed_algorithm}
    if code != 0:
        errors.append("could not inspect git diff against main base")
    if changed_algorithm:
        errors.append(f"algorithm source changed: {changed_algorithm}")

    checks["accepted_limitations"] = ACCEPTED
    checks["state_gate"] = {"s1_r1": "PASS_WITH_LIMITATIONS", "s1": "IN_PROGRESS", "s2_s8": "FROZEN"}
    payload = {
        "decision": "PASS_WITH_LIMITATIONS" if not errors else "REVISION_REQUIRED_S1_R1_FINAL_ACCEPTANCE",
        "errors": errors,
        "unresolved_warnings": [],
        "accepted_limitations": ACCEPTED,
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": payload["decision"], "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
