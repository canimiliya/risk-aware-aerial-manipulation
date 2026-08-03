"""Generate bounded, official mode-3 task constraints from detected violations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from .project_arm_point_to_envelope import project_event


def build_mode3_row(projected: dict[str, Any]) -> list[float]:
    """Build only fields consumed by the official mode-3 contract plus zero padding."""
    return [3.0, *projected["base_point_WB_m"], *projected["arm_point_A0_m"], *([0.0] * 13)]


def generate_constraints(violation: dict[str, Any], max_intervals: int = 1,
                         variant: str = "nominal") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for interval_index, interval in enumerate(violation.get("violating_intervals", [])[:max_intervals]):
        for event_name in ("entry", "minimum", "exit"):
            projected = project_event(interval[event_name], variant=variant)
            projected.update({"interval_index": interval_index, "event_name": event_name, "mode": 3.0})
            projected["mode3_row"] = build_mode3_row(projected)
            rows.append(projected)
    if len(rows) > 6:
        raise ValueError("one adaptive round may add at most six mode-3 rows")
    return rows


def build_task(baseline_path: Path, output_path: Path, added_rows: list[dict[str, Any]],
               insertion_after_mode3: int = 0) -> dict[str, Any]:
    baseline = yaml.safe_load(baseline_path.read_text(encoding="utf-8"))
    result: dict[str, Any] = {}
    for task_name, task in baseline.items():
        copied = dict(task)
        points = [list(row) for row in task["inter_points"]]
        mode3_indices = [i for i, row in enumerate(points) if int(row[0]) == 3]
        insert_at = mode3_indices[min(insertion_after_mode3, len(mode3_indices))] if mode3_indices else len(points)
        if insertion_after_mode3 < len(mode3_indices):
            insert_at = mode3_indices[insertion_after_mode3]
        else:
            insert_at = len(points) - 1
        rows = [list(item["mode3_row"]) for item in added_rows]
        copied["inter_points"] = points[:insert_at] + rows + points[insert_at:]
        # The official task contract counts path segments; the baseline has
        # 9 inter-points and num_points=8.  Preserve that relationship after
        # inserting adaptive points.
        copied["num_points"] = max(0, len(copied["inter_points"]) - 1)
        result[task_name] = copied
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(result, sort_keys=False), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--violation", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output-task", type=Path, required=True)
    parser.add_argument("--output-constraints", type=Path, required=True)
    parser.add_argument("--max-intervals", type=int, default=1)
    parser.add_argument("--insert-after-mode3", type=int, default=0)
    args = parser.parse_args()
    violation = json.loads(args.violation.read_text(encoding="utf-8"))
    rows = generate_constraints(violation, max_intervals=args.max_intervals)
    build_task(args.baseline, args.output_task, rows, insertion_after_mode3=args.insert_after_mode3)
    args.output_constraints.parent.mkdir(parents=True, exist_ok=True)
    args.output_constraints.write_text(json.dumps({"new_mode3": rows, "count": len(rows), "projection_only": True}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"new_mode3": len(rows), "task": str(args.output_task)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
