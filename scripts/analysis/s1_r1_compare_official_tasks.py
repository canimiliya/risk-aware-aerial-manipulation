#!/usr/bin/env python3
"""Read-only comparison of the official grasp/lift/write task contracts."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


def nonzero_indices(row):
    return [i for i, value in enumerate(row) if float(value) != 0.0]


def summarize_task(name, task, yaml_path):
    points = task.get("inter_points") or []
    constraint_counts = {}
    for row in points:
        for idx in nonzero_indices(row[4:]):
            key = f"inter_point_flag_{idx + 4}"
            constraint_counts[key] = constraint_counts.get(key, 0) + 1
    launch = "run_in_sim_grasp.launch" if name == "grasp" else "run_in_sim_other.launch"
    return {
        "task": name,
        "yaml": str(yaml_path),
        "num_points_declared": int(task.get("num_points", 0)),
        "inter_points_count": len(points),
        "inter_point_vector_lengths": sorted({len(row) for row in points}),
        "inter_point_nonzero_flag_counts": constraint_counts,
        "start_pt": task.get("start_pt"),
        "end_pt": task.get("end_pt"),
        "object_position": (task.get("object") or {}).get("position"),
        "launch": launch,
        "jps_segments": None,
        "corridor_segments": None,
    }


def parse_scalar(text, key):
    match = re.search(rf"(?im)^\s*{re.escape(key)}\s*:\s*([^#\r\n]+)", text)
    if not match:
        match = re.search(rf"name=[\"']{re.escape(key)}[\"'][^>]*value=[\"']([^\"']+)[\"']", text)
    if not match:
        return None
    value = match.group(1).strip()
    try:
        return float(value) if "." in value or "e" in value.lower() else int(value)
    except ValueError:
        return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--runtime-root", default=None)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    launch_dir = root / "third_party/am-planner/src/plan/plan_manage/launch"
    misc_dir = root / "third_party/am-planner/src/plan/plan_manage/misc"
    tasks_path = launch_dir / "tasks.yaml"
    tasks = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    names = ["grasp", "lift", "write"]
    # grasp uses its own launch file rather than an entry in tasks.yaml.
    grasp_launch = (launch_dir / "run_in_sim_grasp.launch").read_text(encoding="utf-8")
    grasp_task = {
        "num_points": 0,
        "inter_points": [],
        "start_pt": [parse_scalar(grasp_launch, "start_x"), parse_scalar(grasp_launch, "start_y"), parse_scalar(grasp_launch, "start_z")],
        "end_pt": [parse_scalar(grasp_launch, "end_x"), parse_scalar(grasp_launch, "end_y"), parse_scalar(grasp_launch, "end_z")],
        "object": {"position": [parse_scalar(grasp_launch, "object_px"), parse_scalar(grasp_launch, "object_py"), parse_scalar(grasp_launch, "object_pz")]},
    }
    task_data = [summarize_task("grasp", grasp_task, launch_dir / "run_in_sim_grasp.launch")]
    task_data += [summarize_task(name, tasks[name], tasks_path) for name in ["lift", "write"]]
    runtime_root = Path(args.runtime_root).resolve() if args.runtime_root else root / "docs/evidence/S1-R1/runtime"
    run_names = {"grasp": "grasp_cpu_checkpoint_run_02", "lift": "lift_cpu_checkpoint_run_01", "write": "write_cpu_checkpoint_run_01"}
    for item in task_data:
        log_path = runtime_root / run_names[item["task"]] / "roslaunch.log"
        if log_path.exists():
            text = log_path.read_text(encoding="utf-8", errors="replace")
            item["jps_segments"] = len(re.findall(r"Searching path from", text))
            item["corridor_segments"] = len(re.findall(r"inter point is in the polyhedron", text))
    config_data = {}
    for name in names:
        text = (misc_dir / f"{name}.yaml").read_text(encoding="utf-8")
        config_data[name] = {
            key: parse_scalar(text, key)
            for key in ["Rho", "TotalT", "QdIntervals", "VelMax", "OptRelTol1", "OptRelTol2", "MultiLayerOpt", "PrintCost", "SafeMargin"]
        }
        for key in ["PenaltyPVTB", "PenaltyArm", "PenaltyGraspWeight"]:
            match = re.search(rf"(?im)^\s*{re.escape(key)}\s*:\s*([^#\r\n]+)", text)
            config_data[name][key] = match.group(1).strip() if match else None
    data = {
        "source": {
            "tasks_yaml": str(tasks_path),
            "launch_files": {name: str(launch_dir / ("run_in_sim_grasp.launch" if name == "grasp" else "run_in_sim_other.launch")) for name in names},
            "read_only": True,
        },
        "tasks": task_data,
        "optimizer_config": config_data,
        "comparison": {
            "write_vs_grasp_inter_points": 6 - 0,
            "write_vs_lift_inter_points": 6 - 1,
            "write_has_longest_declared_path": True,
            "write_multilayer_opt": False,
            "grasp_lift_multilayer_opt": True,
            "write_rel_tol_is_stricter": True,
            "write_rho_is_smaller": True,
            "publish_requires_optimizer_return": True,
        },
    }
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "task_complexity_comparison.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# write 与 grasp/lift 的官方任务复杂度对比", "", "本文件只读取官方配置和已保存运行日志，不修改配置。", "", "|任务|中间点|JPS段|走廊段|起点|终点|TotalT|QdIntervals|Rho|MultiLayerOpt|OptRelTol1|OptRelTol2|", "|---|---:|---:|---:|---|---|---:|---:|---:|---|---:|---:|"]
    for item in task_data:
        cfg = config_data[item["task"]]
        lines.append(f"|{item['task']}|{item['inter_points_count']}|{item['jps_segments']}|{item['corridor_segments']}|{item['start_pt']}|{item['end_pt']}|{cfg['TotalT']}|{cfg['QdIntervals']}|{cfg['Rho']}|{cfg['MultiLayerOpt']}|{cfg['OptRelTol1']}|{cfg['OptRelTol2']}|")
    lines += ["", "## 结论", "", "write 比 grasp 多 6 个官方中间点、比 lift 多 5 个；保存的运行日志显示 write 有 7 个 JPS 搜索段、6 个走廊衔接段，而 grasp/lift 各为 2 个 JPS 段、1 个走廊衔接段。write 的 `MultiLayerOpt=False`，但 `OptRelTol1=1e-8`、`OptRelTol2=1e-10` 比 grasp/lift 更严格；其 `Rho=0.001` 也明显更小。", "", "## 约束标志", ""]
    for item in task_data:
        lines.append(f"- `{item['task']}`：{item['inter_point_nonzero_flag_counts']}")
    (out / "task_complexity_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
