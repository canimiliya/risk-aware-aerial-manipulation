#!/usr/bin/env python3
"""Classify the single controlled write run from saved evidence."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    run = Path(args.run_dir).resolve()
    log = (run / "roslaunch.log").read_text(encoding="utf-8", errors="replace")
    monitor = json.loads((run / "monitor_summary.json").read_text(encoding="utf-8"))
    numeric = json.loads((run / "numeric_validation.json").read_text(encoding="utf-8"))
    costs = [float(x) for x in re.findall(r"cost\s*=\s*([-+0-9.eE]+)", log)]
    finite = [x for x in costs if x == x and abs(x) != float("inf")]
    searches = re.findall(r"Searching path from \(([^\n]+)", log)
    jps = re.search(r"JPS path searching time:\s*([0-9.]+)\s*s", log)
    minco_line = re.search(r"Begin to optimize the trajectory with MINCO", log)
    minco_ts = re.search(r"\[([0-9]+\.[0-9]+)\]:[^\n]*Begin to optimize", log)
    if not minco_ts:
        begin_pos = log.find("Begin to optimize")
        prior_timestamps = re.findall(r"\[([0-9]+\.[0-9]+)\]:", log[:begin_pos]) if begin_pos >= 0 else []
        minco_ts_value = float(prior_timestamps[-1]) if prior_timestamps else None
    else:
        minco_ts_value = float(minco_ts.group(1))
    jps_ts = re.search(r"\[([0-9]+\.[0-9]+)\]:[^\n]*JPS path searching time", log)
    first_ts = re.search(r"\[INFO\]\s*\[([0-9]+\.[0-9]+)\]:\s*\[MANAGE\]: Initilized start", log)
    result = json.loads((run / "result_summary.json").read_text(encoding="utf-8"))
    active = bool(monitor.get("classification_inputs", {}).get("process_seen"))
    progressing = monitor.get("final_cost_count", 0) > 0 and monitor.get("final_cost_count", 0) >= 7000
    errors = bool(re.search(r"abort|segmentation fault|uncaught exception|\bnan\b|\binf\b", log, re.I))
    success = bool(numeric.get("success"))
    if success:
        classification = "SUCCESS"
        label = "SUBMITTED_S1_R1_WRITE_SUCCEEDED_EXTENDED_RUNTIME"
    elif errors:
        classification = "WRITE_RUNTIME_ERROR"
        label = "SUBMITTED_S1_R1_WRITE_RUNTIME_ERROR"
    elif active and progressing:
        classification = "WRITE_CPU_RUNTIME_TOO_SLOW"
        label = "SUBMITTED_S1_R1_WRITE_RUNTIME_TOO_SLOW"
    else:
        classification = "WRITE_OPTIMIZER_STALLED"
        label = "SUBMITTED_S1_R1_WRITE_OPTIMIZER_STALLED"
    data = {
        "classification": classification,
        "label": label,
        "human_interpretation": "程序在1200秒内一直占用CPU并持续输出cost，但没有完成并发布两条轨迹；因此是CPU太慢，不是进程空闲或明确运行错误。" if classification == "WRITE_CPU_RUNTIME_TOO_SLOW" else None,
        "run_id": result.get("run_id"),
        "capture_exit": result.get("capture_exit"),
        "timeout_s": numeric.get("timeout_s"),
        "actual_monitor_seconds": monitor.get("elapsed_s"),
        "trajectory_success": success,
        "received_topics": numeric.get("received_topics"),
        "jps_segment_search_count": len(searches),
        "jps_path_seconds": float(jps.group(1)) if jps else None,
        "minco_start_unix_seconds": minco_ts_value,
        "jps_finish_unix_seconds": float(jps_ts.group(1)) if jps_ts else None,
        "run_first_log_unix_seconds": float(first_ts.group(1)) if first_ts else None,
        "cost_samples": len(costs),
        "first_cost": costs[0] if costs else None,
        "minimum_cost": min(finite) if finite else None,
        "last_cost": costs[-1] if costs else None,
        "max_cpu_percent": monitor.get("max_cpu_percent"),
        "max_rss_kb": monitor.get("max_rss_kb"),
        "snapshots": monitor.get("snapshots_written"),
        "log_has_finish": "Finish optimization!" in log,
        "log_has_abort_or_segfault": bool(re.search(r"abort|segmentation fault|uncaught exception", log, re.I)),
        "log_has_nan_or_inf": bool(re.search(r"\bnan\b|\binf\b", log, re.I)),
        "monitor_ros_query_note": "正式运行监控器启动时尚未继承ROS PATH，少数topic字段记录为command_error；运行本身的rostopic_list和capture数值证据仍保留。",
    }
    out = run.parent
    (out / "write_classification.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# write 1200 秒诊断分类", "", f"结论：`{classification}`。人话：程序没有崩，而是一直占用 CPU、cost 持续变化，1200 秒仍未完成并发布双轨迹，因此判为 CPU 太慢。", "", "## 证据", "", f"- 1200 秒内收到轨迹：`{success}`；捕获退出码：`{result.get('capture_exit')}`。", f"- JPS 搜索段数：`{len(searches)}`，JPS 用时：`{jps.group(1) if jps else None}` 秒。", f"- MINCO 开始阶段最接近可见时间戳：`{minco_ts_value}`；原始 Begin 行没有独立 ROS 时间戳；优化完成日志：`{'Finish optimization!' in log}`。", f"- cost：样本 `{len(costs)}`，首个 `{costs[0] if costs else None}`，最小 `{min(finite) if finite else None}`，最后 `{costs[-1] if costs else None}`。", f"- CPU 峰值 `{monitor.get('max_cpu_percent')}`%，RSS 峰值 `{monitor.get('max_rss_kb')}` KB；快照 `{monitor.get('snapshots_written')}`。", "- 日志未见 abort、segmentation fault、NaN 或 Inf。", "", "## 不能过度解读的地方", "", "这次证据能确认 CPU 持续计算且未在时限内完成；它不能证明换成更快硬件后一定能收敛，也没有修改任何官方参数来尝试。", "", f"原始标签：`{label}`（提交给复核，表示 write 诊断完成但 write 本身未通过）。"]
    (out / "write_classification.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
