#!/usr/bin/env python3
"""Trace Python ABI dependencies from the preserved GPU build.

This script is intentionally read-only with respect to the old GPU workspace.
It copies link/CMake evidence and records direct ELF NEEDED entries separately
from ldd's resolved runtime graph.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


def run(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    return (result.stdout or "") + (result.stderr or "")


def direct_needed(readelf_text: str) -> list[str]:
    return re.findall(r"Shared library: \[([^\]]+)\]", readelf_text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu-workspace", type=Path, default=Path("/home/amplanner/am-planner-gpu-ws"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    gpu = args.gpu_workspace
    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    link_files = {
        "se3_node": gpu / "build/plan_manage/CMakeFiles/se3_node.dir/link.txt",
        "se3_planner": gpu / "build/traj_opt/CMakeFiles/se3_planner.dir/link.txt",
    }
    for name, source in link_files.items():
        if source.exists():
            shutil.copyfile(source, out / f"{name}_link.txt")

    refs = run(["bash", "-lc", f"grep -RInE 'python3\\.8|python3\\.9|PYTHON_LIBRARY|Python_LIBRARY|Python3_LIBRARY|catkin_LIBRARIES' '{gpu}/build' '{gpu}/.catkin_tools' 2>/dev/null | head -300"])
    (out / "cmake_python_refs.txt").write_text(refs, encoding="utf-8")
    ros_refs = run(["bash", "-lc", "grep -RInE 'python|PYTHON|catkin_LIBRARIES' /opt/ros/noetic/share/roslib/cmake /opt/ros/noetic/share/rospy/cmake /opt/ros/noetic/share/catkin/cmake 2>/dev/null | head -300"])
    (out / "ros_cmake_python_refs.txt").write_text(ros_refs, encoding="utf-8")

    binaries = {
        "se3_node": gpu / "devel/.private/plan_manage/lib/plan_manage/se3_node",
        "libse3_planner.so": gpu / "devel/.private/traj_opt/lib/libse3_planner.so",
        "libroslib.so": Path("/opt/ros/noetic/lib/libroslib.so"),
    }
    graph: dict[str, object] = {"gpu_workspace": str(gpu), "binaries": {}, "classification": "ROOT_CAUSE_UNRESOLVED"}
    all_needed: set[str] = set()
    for name, binary in binaries.items():
        if not binary.exists():
            graph["binaries"][name] = {"path": str(binary), "missing": True}
            continue
        readelf = run(["readelf", "-d", str(binary)])
        objdump = run(["objdump", "-p", str(binary)])
        ldd = run(["ldd", str(binary)])
        (out / f"{name}.readelf-d.txt").write_text(readelf, encoding="utf-8")
        (out / f"{name}.objdump-p.txt").write_text(objdump, encoding="utf-8")
        (out / f"{name}.ldd.txt").write_text(ldd, encoding="utf-8")
        needed = direct_needed(readelf)
        all_needed.update(needed)
        graph["binaries"][name] = {
            "path": str(binary),
            "direct_needed": needed,
            "ldd_python_lines": [line for line in ldd.splitlines() if "python3." in line],
        }

    se3 = graph["binaries"].get("se3_node", {})
    se3_needed = se3.get("direct_needed", []) if isinstance(se3, dict) else []
    roslib = graph["binaries"].get("libroslib.so", {})
    roslib_needed = roslib.get("direct_needed", []) if isinstance(roslib, dict) else []
    has38 = any("python3.8" in item for item in all_needed)
    has39 = any("python3.9" in item for item in all_needed)
    se3_has38 = any("python3.8" in item for item in se3_needed)
    se3_has39 = any("python3.9" in item for item in se3_needed)
    roslib_has38 = any("python3.8" in item for item in roslib_needed)
    if roslib_has38:
        classification = "TRANSITIVE_ROS_LIBRARY_PYTHON38"
    elif se3_has38 and se3_has39:
        classification = "BOTH_DIRECT_AND_TRANSITIVE"
    elif se3_has38:
        classification = "DIRECT_LEGACY_CMAKE_PYTHON_LINK"
    elif has38 and has39:
        classification = "BOTH_DIRECT_AND_TRANSITIVE"
    elif not has38:
        classification = "ROOT_CAUSE_UNRESOLVED"
    graph["classification"] = classification
    graph["direct_vs_transitive"] = {
        "se3_node_direct_needed": se3_needed,
        "libse3_planner_direct_needed": graph["binaries"].get("libse3_planner.so", {}).get("direct_needed", []),
        "libroslib_direct_needed": roslib_needed,
        "all_python_needed": sorted(x for x in all_needed if "python3." in x),
    }
    (out / "python_abi_graph.json").write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Python ABI graph",
        "",
        f"- classification: `{classification}`",
        "- direct NEEDED: read from each ELF's `readelf -d` output",
        "- transitive/runtime resolution: read from each ELF's `ldd` output",
        "",
    ]
    for name, item in graph["binaries"].items():
        if isinstance(item, dict):
            lines.append(f"## {name}")
            lines.append(f"- path: `{item.get('path')}`")
            lines.append(f"- direct NEEDED: {', '.join(item.get('direct_needed', []))}")
            lines.append(f"- ldd Python lines: {' | '.join(item.get('ldd_python_lines', []))}")
            lines.append("")
    (out / "python_abi_graph.md").write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
