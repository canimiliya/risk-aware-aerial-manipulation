#!/usr/bin/env python3
"""Evidence-completeness audit for the R5 write-only diagnosis."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


EXPECTED_BRANCH = "agent/s1-r1-am-planner-install-basic-repro"
EXPECTED_SOURCE = "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d"
EXPECTED_ORIGINAL_SHA = "506f59645e3e076c3910774054d0538a7664362e39cecb9b06e2d5e01aecca49"


def run(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    return result.returncode, (result.stdout or "").strip(), (result.stderr or "").strip()


def main():
    root = Path(__file__).resolve().parents[2]
    errors, warnings, checks = [], [], []

    def check(name, condition, detail=""):
        checks.append({"name": name, "ok": bool(condition), "detail": detail})
        if not condition:
            errors.append(f"{name}: {detail}")

    branch = run(["git", "branch", "--show-current"], root)[1]
    check("branch", branch == EXPECTED_BRANCH, branch)
    wsl_cmd = "cd /home/amplanner/am-planner-ws/src/am-planner; printf 'HEAD=%s\\n' \"$(git rev-parse HEAD)\"; printf 'STATUS_BEGIN\\n'; git status --short; printf 'STATUS_END\\n'; sha256sum src/plan/traj_opt/weights/workspace_probability_weight.pth; findmnt -T src/plan/traj_opt/weights/workspace_probability_weight.pth"
    rc, wsl_out, wsl_err = run(["wsl", "-d", "AMPlanner-Ubuntu20", "--exec", "bash", "-lc", wsl_cmd])
    lines = wsl_out.splitlines()
    source_head = lines[0].removeprefix("HEAD=") if lines else ""
    try:
        source_status = "\n".join(lines[lines.index("STATUS_BEGIN") + 1:lines.index("STATUS_END")])
    except ValueError:
        source_status = "missing"
    original_sha = next((line.split()[0] for line in lines if line.startswith(EXPECTED_ORIGINAL_SHA)), "")
    mount_line = next((line for line in lines if line.startswith("/")), "")
    check("official_source_commit", rc == 0 and source_head == EXPECTED_SOURCE, source_head)
    check("official_source_clean", source_status == "", repr(source_status))
    check("official_weight_restored", original_sha == EXPECTED_ORIGINAL_SHA, original_sha)
    check("no_residual_bind_mount", "workspace_probability_weight_cpu.pth" not in wsl_out and mount_line.startswith("/"), mount_line)

    diagnosis = root / "docs/evidence/S1-R1/write_diagnosis"
    run_dir = root / "docs/evidence/S1-R1/write_diagnosis_run_01"
    required = [
        diagnosis / "task_complexity_comparison.json", diagnosis / "task_complexity_comparison.md",
        diagnosis / "optimizer_static_contract.md", diagnosis / "existing_log_comparison.json",
        diagnosis / "existing_log_comparison.md", diagnosis / "workspace_model_cpu_benchmark.json",
        diagnosis / "workspace_model_cpu_benchmark.md", diagnosis / "write_classification.json",
        diagnosis / "write_classification.md", run_dir / "result_summary.json", run_dir / "numeric_validation.json",
        run_dir / "monitor_samples.jsonl", run_dir / "monitor_summary.json", run_dir / "cost_series.csv",
    ]
    for path in required:
        check(f"evidence:{path.name}", path.exists() and path.stat().st_size > 0, str(path))
    for mark in [60, 300, 600, 900, 1200]:
        path = run_dir / f"snapshot_{mark}s.json"
        check(f"snapshot:{mark}s", path.exists() and path.stat().st_size > 0, str(path))

    classification = json.loads((diagnosis / "write_classification.json").read_text(encoding="utf-8"))
    check("classification", classification.get("classification") == "WRITE_CPU_RUNTIME_TOO_SLOW", classification.get("classification"))
    numeric = json.loads((run_dir / "numeric_validation.json").read_text(encoding="utf-8"))
    check("write_no_false_success", numeric.get("success") is False and numeric.get("received_topics") == [], str(numeric))
    monitor = json.loads((run_dir / "monitor_summary.json").read_text(encoding="utf-8"))
    check("monitor_samples", monitor.get("sample_count", 0) >= 200, str(monitor.get("sample_count")))
    check("monitor_progress", monitor.get("final_cost_count", 0) > 7000 and monitor.get("max_cpu_percent", 0) > 1000, str(monitor))
    benchmark = json.loads((diagnosis / "workspace_model_cpu_benchmark.json").read_text(encoding="utf-8"))
    check("benchmark_batches", [row.get("batch") for row in benchmark.get("rows", [])] == [1, 96, 192, 576, 960], str(benchmark.get("rows")))
    check("benchmark_cpu", benchmark.get("cuda_available") is False, str(benchmark.get("cuda_available")))

    milestone = (root / "docs/milestones/S1_R1_status.md").read_text(encoding="utf-8")
    master = (root / "01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.4.md").read_text(encoding="utf-8")
    check("s1_in_progress", "IN_PROGRESS" in milestone and "S1：`IN_PROGRESS`" in master)
    check("s2_frozen", "S2--S8" in milestone and "FROZEN" in milestone and "S2--S8：`FROZEN`" in master)
    check("write_only_run", "task=write" in (run_dir / "command.txt").read_text(encoding="utf-8") and "grasp" not in (run_dir / "command.txt").read_text(encoding="utf-8") and "lift" not in (run_dir / "command.txt").read_text(encoding="utf-8"))

    changed_third_party = run(["git", "status", "--short", "--", "third_party/am-planner"], root)[1]
    check("no_official_source_changes", changed_third_party == "", changed_third_party)
    cpu_weight_files = [p for p in root.rglob("*.pth") if "workspace_probability_weight_cpu" in p.name]
    check("no_cpu_weight_submitted", not cpu_weight_files, ", ".join(str(p) for p in cpu_weight_files))
    large = [p for p in root.rglob("*") if p.is_file() and p.stat().st_size > 10 * 1024 * 1024 and ".git" not in p.parts and "third_party" not in p.parts]
    check("no_large_artifacts", not large, ", ".join(str(p) for p in large[:5]))
    diff_rc, _, diff_err = run(["git", "diff", "--check"], root)
    check("git_diff_check", diff_rc == 0, diff_err)

    data = {"errors": len(errors), "warnings": len(warnings), "checks": checks, "error_details": errors, "warning_details": warnings}
    out = diagnosis / "write_diagnosis_audit.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# S1-R1 write 诊断自动检查", "", f"errors={len(errors)} warnings={len(warnings)}"]
    lines += [f"- {'PASS' if item['ok'] else 'FAIL'} {item['name']}: {item.get('detail', '')}" for item in checks]
    (diagnosis / "write_diagnosis_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"errors={len(errors)} warnings={len(warnings)}")
    for item in errors:
        print(f"ERROR: {item}")
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
