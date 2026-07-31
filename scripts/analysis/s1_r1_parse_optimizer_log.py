#!/usr/bin/env python3
"""Parse preserved AM-Planner logs without touching the upstream source."""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


def parse_one(path: Path, expected_runtime=None):
    text = path.read_text(encoding="utf-8", errors="replace")
    costs = []
    for match in re.finditer(r"cost\s*=\s*([-+0-9.eE]+)", text):
        try:
            value = float(match.group(1))
            costs.append(value)
        except ValueError:
            pass
    jps = re.search(r"JPS path searching time:\s*([0-9.]+)\s*s", text)
    opt = re.search(r"Optimization time usage:\s*([0-9.]+)\s*ms", text)
    final = re.search(r"Final cost:\s*([-+0-9.eE]+)", text)
    duration = re.search(r"Total Duration:\s*([-+0-9.eE]+)", text)
    runtime = float(expected_runtime) if expected_runtime is not None else None
    finite = [x for x in costs if math.isfinite(x)]
    def rate(window):
        if len(costs) < 2:
            return None
        values = costs[-min(window, len(costs)):]
        return (values[0] - values[-1]) / max(abs(values[0]), 1.0)
    result = {
        "log": str(path),
        "jps_seconds": float(jps.group(1)) if jps else None,
        "optimization_ms": float(opt.group(1)) if opt else None,
        "total_duration": float(duration.group(1)) if duration else None,
        "final_cost_reported": float(final.group(1)) if final else None,
        "cost_samples": len(costs),
        "first_cost": costs[0] if costs else None,
        "last_cost": costs[-1] if costs else None,
        "minimum_cost": min(finite) if finite else None,
        "maximum_cost": max(finite) if finite else None,
        "nan_count": text.lower().count("nan"),
        "inf_count": text.lower().count("inf"),
        "recent_10_relative_drop": rate(10),
        "recent_50_relative_drop": rate(50),
        "recent_100_relative_drop": rate(100),
        "cost_outputs_per_minute": (len(costs) / runtime * 60.0) if runtime else None,
        "runtime_seconds_basis": runtime,
        "has_finish_log": "Finish optimization!" in text,
        "has_abort_or_segfault": bool(re.search(r"abort|segmentation fault|uncaught exception", text, re.I)),
        "has_error_lines": bool(re.search(r"\[ERROR\]|failed to setup", text, re.I)),
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    base = root / "docs/evidence/S1-R1/runtime"
    inputs = {
        "grasp": (base / "grasp_cpu_checkpoint_run_02/roslaunch.log", 300),
        "lift": (base / "lift_cpu_checkpoint_run_01/roslaunch.log", 300),
        "write_300s": (base / "write_cpu_checkpoint_run_01/roslaunch.log", 300),
    }
    rows = {name: parse_one(path, runtime) for name, (path, runtime) in inputs.items()}
    data = {"source": "preserved runtime logs", "runs": rows}
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "existing_log_comparison.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# 既有运行日志对比", "", "|运行|JPS(s)|优化(ms)|cost样本|首个cost|最小cost|最后cost|最近100下降率|完成日志|", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for name, row in rows.items():
        lines.append(f"|{name}|{row['jps_seconds']}|{row['optimization_ms']}|{row['cost_samples']}|{row['first_cost']}|{row['minimum_cost']}|{row['last_cost']}|{row['recent_100_relative_drop']}|{row['has_finish_log']}|")
    lines += ["", "write 的 300 秒原始日志没有完成日志，但 cost 持续输出且总体下降；这只能说明当时仍在推进，不能单独证明最终会收敛。", ""]
    (out / "existing_log_comparison.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
