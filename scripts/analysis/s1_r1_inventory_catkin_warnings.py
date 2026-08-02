#!/usr/bin/env python3
"""Inventory Catkin warning-bearing packages from an unfiltered build log.

This parser intentionally reads the raw catkin output and preserves the
warning text. It does not filter warnings from the source log or claim that a
warning-free build occurred.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from pathlib import Path


SECTION_RE = re.compile(r"^Warnings << (?P<package>[^:]+):(?P<stage>\S+) (?P<path>\S+)")
WARNING_MARKERS = (
    "CMake Warning",
    "** WARNING **",
    "warning:",
)


def classify(text: str) -> str:
    lower = text.lower()
    if any(token in lower for token in ("python3.8", "python 3.8", "abi", "undefined reference", "not found")):
        return "ABI/Python"
    if any(token in lower for token in ("cuda", "sm_", "architecture")):
        return "CUDA 架构"
    if any(token in lower for token in ("trajectory", "polynomial", "segment duration")):
        return "轨迹相关"
    if "deprecated" in lower or "deprecation" in lower:
        return "编译器弃用/上游提示"
    if "unused" in lower or "not used" in lower:
        return "未使用变量/依赖"
    if "cmakelists.txt" in lower or "catkin_package" in lower or "add_executable" in lower or "add_library" in lower:
        return "ROS/CMake"
    return "官方第三方源码/编译器提示"


def parse(log_path: Path) -> OrderedDict[str, dict]:
    records: OrderedDict[str, dict] = OrderedDict()
    current = None
    for line_number, raw in enumerate(log_path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        match = SECTION_RE.match(raw)
        if match:
            package = match.group("package")
            current = records.setdefault(package, {
                "package": package,
                "warning_count": 0,
                "stages": [],
                "warning_summaries": [],
                "warning_files": [],
                "source_categories": [],
                "raw_log": str(log_path).replace("\\", "/"),
            })
            current["stages"].append(match.group("stage"))
            current["warning_files"].append(match.group("path"))
            continue
        if current is None:
            continue
        if any(marker in raw for marker in WARNING_MARKERS):
            current["warning_count"] += 1
            clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", raw).strip()
            if clean and clean not in current["warning_summaries"]:
                current["warning_summaries"].append(clean)
            category = classify(clean)
            if category not in current["source_categories"]:
                current["source_categories"].append(category)

    for record in records.values():
        record["stages"] = list(dict.fromkeys(record["stages"]))
        record["warning_files"] = list(dict.fromkeys(record["warning_files"]))
        if not record["source_categories"]:
            record["source_categories"] = ["官方第三方源码/编译器提示"]
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    records = parse(args.log)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_log": str(args.log).replace("\\", "/"),
        "warning_bearing_package_count": len(records),
        "packages": list(records.values()),
        "classification_policy": {
            "blocking_keywords": ["Python 3.8", "ABI", "undefined reference", "CUDA architecture", "trajectory"],
            "note": "Counts and summaries are derived from raw unfiltered catkin output; no warning text was removed.",
        },
    }
    (args.output_dir / "catkin_warning_inventory.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Catkin warning inventory",
        "",
        f"- Raw log: `{payload['source_log']}`",
        f"- Warning-bearing packages: **{len(records)}**",
        "- Policy: raw warning text is preserved; this inventory does not filter warnings.",
        "",
        "| Package | Warning count | Stages | Source category |",
        "|---|---:|---|---|",
    ]
    for record in records.values():
        lines.append(
            f"| `{record['package']}` | {record['warning_count']} | {', '.join(record['stages'])} | "
            f"{'; '.join(record['source_categories'])} |"
        )
    lines.extend(["", "## Warning summaries", ""])
    for record in records.values():
        lines.extend([
            f"### `{record['package']}`",
            "",
            f"- Files: {', '.join(f'`{item}`' for item in record['warning_files'])}",
            f"- Classification: {', '.join(record['source_categories'])}",
            "- Deduplicated raw warning lines:",
        ])
        lines.extend(f"  - `{item}`" for item in record["warning_summaries"])
        lines.append("")
    (args.output_dir / "catkin_warning_inventory.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"packages": len(records), "output_dir": str(args.output_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
