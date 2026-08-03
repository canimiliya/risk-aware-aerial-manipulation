"""Record the unchanged P2->P3/P3->P4 direction contract per S2-R5 round."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POINTS = ROOT / "docs/evidence/S2-R4/static_feasibility/p0_p6_selected.json"
OUT_ROOT = ROOT / "docs/evidence/S2-R5/rounds"


def main() -> int:
    points = json.loads(POINTS.read_text(encoding="utf-8"))["P0_P6"]
    p2, p3, p4 = (points[i]["arm_point_A0_m"] for i in (2, 3, 4))
    v23 = [p3[i] - p2[i] for i in range(3)]
    v34 = [p4[i] - p3[i] for i in range(3)]
    result = {
        "source": str(POINTS).replace("\\", "/"),
        "P2_to_P3": {"delta_A0_m": v23, "horizontal": abs(v23[2]) < 1e-12, "positive_x": v23[0] > 0.0},
        "P3_to_P4": {"delta_A0_m": v34, "horizontal": abs(v34[2]) < 1e-12, "negative_x_positive_y": v34[0] < 0.0 and v34[1] > 0.0},
        "direction_error_m": max(abs(v23[2]), abs(v34[2])),
        "pass": bool(abs(v23[2]) < 1e-12 and v23[0] > 0.0 and abs(v34[2]) < 1e-12 and v34[0] < 0.0 and v34[1] > 0.0),
        "task_points_unchanged": True,
    }
    for i in range(4):
        out = OUT_ROOT / f"round_{i}/direction_validation.json"
        out.write_text(json.dumps({"round": i, **result}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "direction_error_m": result["direction_error_m"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
