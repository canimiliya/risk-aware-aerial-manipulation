#!/usr/bin/env python3
"""Monitor a GPU AM-Planner run without changing the official process."""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import time
from pathlib import Path

SNAPSHOTS = [60, 300, 600, 900, 1200]

def command(args: list[str], timeout: int = 8) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False).stdout.strip()
    except Exception as exc:
        return f"command_error:{type(exc).__name__}:{exc}"

def process_rows() -> list[dict]:
    text = command(["ps", "-eo", "pid,ppid,stat,pcpu,rss,vsz,nlwp,etimes,args", "--no-headers"])
    rows = []
    for line in text.splitlines():
        parts = line.strip().split(None, 8)
        if len(parts) < 9 or "se3_node" not in parts[8] or "grep" in parts[8]:
            continue
        try:
            rows.append({"pid": int(parts[0]), "ppid": int(parts[1]), "state": parts[2], "cpu_percent": float(parts[3]), "rss_kb": int(parts[4]), "vsz_kb": int(parts[5]), "threads": int(parts[6]), "elapsed_s": int(parts[7]), "args": parts[8]})
        except ValueError:
            continue
    return rows

def gpu_state() -> dict:
    raw = command(["nvidia-smi", "--query-compute-apps=pid,name,used_memory", "--format=csv,noheader,nounits"])
    util = command(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"])
    apps = []
    for line in raw.splitlines():
        fields = [item.strip() for item in line.split(",")]
        if len(fields) >= 3:
            try:
                apps.append({"pid": int(fields[0]), "name": fields[1], "used_memory_mb": int(float(fields[2]))})
            except ValueError:
                pass
    fields = [item.strip() for item in util.split(",")]
    gpu = {}
    if len(fields) >= 3:
        try:
            gpu = {"utilization_percent": float(fields[0]), "memory_used_mb": float(fields[1]), "memory_total_mb": float(fields[2])}
        except ValueError:
            gpu = {"raw": util}
    return {"apps": apps, "gpu": gpu, "raw_apps": raw, "raw_gpu": util, "se3_gpu_pid_seen": any("se3_node" in item.get("name", "") for item in apps)}

def topic_state() -> dict:
    state = {}
    for topic in ["/trajectory", "/trajectory_arm"]:
        info = command(["/opt/ros/noetic/bin/rostopic", "info", topic])
        state[topic] = {"raw": info, "has_publishers": "Publishers:" in info and "* /" in info}
    return state

def costs_from_log(path: Path) -> list[float]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [float(value) for value in re.findall(r"cost\s*=\s*([-+0-9.eE]+)", text)]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--timeout-s", type=int, required=True)
    args = parser.parse_args()
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    seen_costs = 0
    snapshots: list[int] = []
    max_cpu = 0.0
    max_rss = 0
    max_gpu_util = 0.0
    max_gpu_mem = 0.0
    gpu_pid_seen = False
    sample_count = 0
    costs: list[float] = []
    with (run_dir / "monitor_samples.jsonl").open("w", encoding="utf-8") as samples, (run_dir / "cost_series.csv").open("w", encoding="utf-8", newline="") as cost_file:
        writer = csv.writer(cost_file)
        writer.writerow(["elapsed_s", "cost"])
        while True:
            elapsed = time.monotonic() - start
            process = process_rows()
            gpu = gpu_state()
            gpu_pid_seen = gpu_pid_seen or bool(gpu["se3_gpu_pid_seen"])
            fields = gpu.get("gpu", {})
            if isinstance(fields, dict):
                max_gpu_util = max(max_gpu_util, float(fields.get("utilization_percent", 0.0) or 0.0))
                max_gpu_mem = max(max_gpu_mem, float(fields.get("memory_used_mb", 0.0) or 0.0))
            costs = costs_from_log(run_dir / "roslaunch.log")
            finite = [value for value in costs if value == value and abs(value) != float("inf")]
            sample = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "elapsed_s": round(elapsed, 3), "se3_node": process, "gpu": gpu, "cost_count": len(costs), "latest_cost": costs[-1] if costs else None, "minimum_cost": min(finite) if finite else None, "topics": topic_state() if sample_count % 6 == 0 else None}
            samples.write(json.dumps(sample, ensure_ascii=False) + "\n")
            samples.flush()
            while seen_costs < len(costs):
                writer.writerow([round(elapsed, 3), costs[seen_costs]])
                seen_costs += 1
            cost_file.flush()
            sample_count += 1
            if process:
                max_cpu = max(max_cpu, max(row["cpu_percent"] for row in process))
                max_rss = max(max_rss, max(row["rss_kb"] for row in process))
            for mark in SNAPSHOTS:
                if mark not in snapshots and elapsed >= mark:
                    snapshot = dict(sample)
                    snapshot["snapshot_s"] = mark
                    (run_dir / f"snapshot_{mark}s.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
                    snapshots.append(mark)
            if (run_dir / "result_summary.json").exists() and ((run_dir / "numeric_validation.json").exists() or elapsed > 30):
                break
            if elapsed >= args.timeout_s + 20:
                break
            time.sleep(5)
    finite = [value for value in costs if value == value and abs(value) != float("inf")]
    summary = {"monitor_started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "sample_count": sample_count, "elapsed_s": round(time.monotonic() - start, 3), "snapshots_written": snapshots, "max_cpu_percent": max_cpu, "max_rss_kb": max_rss, "max_gpu_utilization_percent": max_gpu_util, "max_gpu_memory_used_mb": max_gpu_mem, "se3_gpu_pid_seen": gpu_pid_seen, "final_cost_count": seen_costs, "final_latest_cost": costs[-1] if costs else None, "final_minimum_cost": min(finite) if finite else None, "result_summary_present": (run_dir / "result_summary.json").exists(), "classification_inputs": {"process_seen": bool(process), "log_costs_seen": bool(costs), "gpu_process_seen": gpu_pid_seen, "trajectory_numeric_validation_present": (run_dir / "numeric_validation.json").exists()}}
    (run_dir / "monitor_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "monitor_summary.md").write_text("\n".join(["# GPU 运行监控摘要", "", f"采样 {sample_count} 次；快照：{snapshots}。", f"se3_node 被 nvidia-smi 观察到：{gpu_pid_seen}。GPU 峰值利用率：{max_gpu_util:.2f}%；峰值显存：{max_gpu_mem:.0f} MB。", f"CPU 峰值：{max_cpu:.2f}%；RSS 峰值：{max_rss} KB；cost 样本：{seen_costs}。", "", "监控只记录运行现场；是否通过由轨迹文件、数值校验和官方日志共同决定。", ""]) + "\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
