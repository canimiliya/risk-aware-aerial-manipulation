"""Read back corrected S3-R0 scene AABBs from an exported Isaac USD stage."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from planner_bridge.scenes.s3_r0_scene_contract import SCENE_AABBS, SCENE_AABB_FRAME


PRIM_PATHS = {
    "TargetProxy": "/World/TargetProxy",
    "MainBeam": "/World/Crossarm/MainBeam",
    "Column": "/World/Crossarm/Column",
    "AdjacentObstacle": "/World/Crossarm/AdjacentObstacle",
}
TOLERANCE_M = 1e-9


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(stage_path: Path) -> dict[str, object]:
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(stage_path))
    if stage is None:
        raise RuntimeError(f"could not open USD stage: {stage_path}")
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy", "guide"])
    rows: dict[str, object] = {}
    overall = True
    for name, prim_path in PRIM_PATHS.items():
        prim = stage.GetPrimAtPath(prim_path)
        if not prim or not prim.IsValid():
            rows[name] = {"prim_path": prim_path, "readback_status": "MISSING", "pass": False}
            overall = False
            continue
        bound = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        lower = [float(v) for v in bound.GetMin()]
        upper = [float(v) for v in bound.GetMax()]
        center = [(lo + hi) / 2.0 for lo, hi in zip(lower, upper)]
        size = [hi - lo for lo, hi in zip(lower, upper)]
        contract = SCENE_AABBS[name]
        contract_center = list(contract.center_m)
        contract_size = list(contract.size_m)
        contract_min = list(contract.min_m)
        contract_max = list(contract.max_m)
        errors = {
            "center_m": [abs(a - b) for a, b in zip(center, contract_center)],
            "size_m": [abs(a - b) for a, b in zip(size, contract_size)],
            "min_m": [abs(a - b) for a, b in zip(lower, contract_min)],
            "max_m": [abs(a - b) for a, b in zip(upper, contract_max)],
        }
        passed = all(value <= TOLERANCE_M for values in errors.values() for value in values)
        overall = overall and passed
        rows[name] = {
            "prim_path": prim_path,
            "contract_center_m": contract_center,
            "contract_size_m": contract_size,
            "contract_min_m": contract_min,
            "contract_max_m": contract_max,
            "readback_center_m": center,
            "readback_size_m": size,
            "readback_min_m": lower,
            "readback_max_m": upper,
            "absolute_error_m": errors,
            "pass": passed,
        }
    return {
        "decision": "PASS" if overall else "FAIL",
        "coordinate_frame": SCENE_AABB_FRAME,
        "tolerance_m": TOLERANCE_M,
        "stage_path": str(stage_path),
        "stage_sha256": _sha256(stage_path),
        "boxes": rows,
        "column_required_z_bounds_m": [0.08, 1.38],
        "column_readback_z_bounds_m": rows.get("Column", {}).get("readback_min_m", [None, None, None])[2:3] + rows.get("Column", {}).get("readback_max_m", [None, None, None])[2:3] if isinstance(rows.get("Column"), dict) else [],
        "overall_pass": overall,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "hide_ui": True, "disable_viewport_updates": True})
    try:
        result = run(args.stage)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        app.close(wait_for_replicator=False, skip_cleanup=True)
    return 0 if result["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
