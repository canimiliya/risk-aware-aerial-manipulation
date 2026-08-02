#!/usr/bin/env python3
"""Low-interference write monitor using /proc, ps and ROS CLI queries."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import time
from pathlib import Path


SNAPSHOTS = [60, 300, 600, 900, 1200]


def command(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=8, check=False).stdout.strip()
    except Exception as exc:
        return f"command_error:{exc}"


def process_rows():
    text = command(["ps", "-eo", "pid,ppid,stat,pcpu,rss,vsz,nlwp,etimes,args", "--no-headers"])
    rows = []
    for line in text.splitlines():
        parts = line.strip().split(None, 8)
        if len(parts) < 9:
            continue
        if "se3_node" not in parts[8] or "grep" in parts[8]:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        io = {}
        try:
            for item in Path(f"/proc/{pid}/io").read_text().splitlines():
                if ":" in item:
                    key, value = item.split(":", 1)
                    io[key.strip()] = int(value.strip())
            status = Path(f"/proc/{pid}/status").read_text(errors="replace")
            for key in ["voluntary_ctxt_switches", "nonvoluntary_ctxt_switches"]:
                match = re.search(rf"^{key}:\s*(\d+)", status, re.M)
                if match:
                    io[key] = int(match.group(1))
        except OSError:
            pass
        rows.append({"pid": pid, "ppid": int(parts[1]), "state": parts[2], "cpu_percent": float(parts[3]), "rss_kb": int(parts[4]), "vsz_kb": int(parts[5]), "threads": int(parts[6]), "elapsed_s": int(parts[7]), "args": parts[8], "io": io})
    return rows


def costs_from_log(log_path):
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [float(value) for value in re.findall(r"cost\s*=\s*([-+0-9.eE]+)", text)]


def topic_state():
    state = {}
    rostopic = "/opt/ros/noetic/bin/rostopic"
    for topic in ["/trajectory", "/trajectory_arm"]:
        info = command([rostopic, "info", topic])
        state[topic] = {"raw": info, "has_publishers": "Publishers:" in info and "* /" in info}
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--timeout-s", type=int, default=1200)
    args = parser.parse_args()
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    samples_path = run_dir / "monitor_samples.jsonl"
    cost_csv = run_dir / "cost_series.csv"
    start = time.monotonic()
    seen_costs = 0
    snapshots = []
    max_cpu = 0.0
    max_rss = 0
    sample_count = 0
    with samples_path.open("w", encoding="utf-8") as samples, cost_csv.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["elapsed_s", "cost"])
        while True:
            elapsed = time.monotonic() - start
            process = process_rows()
            log_path = run_dir / "roslaunch.log"
            costs = costs_from_log(log_path)
            recent = costs[-20:]
            recent_rate = None
            if len(recent) >= 2:
                recent_rate = (recent[0] - recent[-1]) / max(abs(recent[0]), 1.0)
            latest = costs[-1] if costs else None
            finite = [value for value in costs if value == value and abs(value) != float("inf")]
            log_stat = None
            try:
                stat = log_path.stat()
                log_stat = {"size": stat.st_size, "mtime": stat.st_mtime}
            except OSError:
                pass
            sample = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "elapsed_s": round(elapsed, 3), "se3_node": process, "log": log_stat, "cost_count": len(costs), "latest_cost": latest, "minimum_cost": min(finite) if finite else None, "recent_20_relative_drop": recent_rate, "topics": topic_state() if sample_count % 6 == 0 else None}
            samples.write(json.dumps(sample, ensure_ascii=False) + "\n")
            samples.flush()
            while seen_costs < len(costs):
                writer.writerow([round(elapsed, 3), costs[seen_costs]])
                seen_costs += 1
            csv_file.flush()
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
            result = run_dir / "result_summary.json"
            numeric = run_dir / "numeric_validation.json"
            if result.exists() and (numeric.exists() or elapsed > 30):
                break
            if elapsed >= args.timeout_s + 20:
                break
            time.sleep(5)
    summary = {"monitor_started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start + time.time() - time.monotonic())), "sample_count": sample_count, "elapsed_s": round(time.monotonic() - start, 3), "snapshots_written": snapshots, "max_cpu_percent": max_cpu, "max_rss_kb": max_rss, "final_cost_count": seen_costs, "final_latest_cost": costs[-1] if costs else None, "final_minimum_cost": min(finite) if finite else None, "result_summary_present": (run_dir / "result_summary.json").exists(), "classification_inputs": {"process_seen": bool(process), "log_costs_seen": bool(costs), "trajectory_numeric_validation_present": (run_dir / "numeric_validation.json").exists()}}
    (run_dir / "monitor_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# write 低干扰监控摘要", "", f"采样 {sample_count} 次，写入快照：{snapshots}。", f"最高 CPU：{max_cpu:.2f}%；最高 RSS：{max_rss} KB；最终 cost 样本：{seen_costs}。", "", "分类依据：监控只记录现场，不替代官方运行结果；最终分类由进程、日志/cost变化和轨迹文件共同决定。"]
    (run_dir / "monitor_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
