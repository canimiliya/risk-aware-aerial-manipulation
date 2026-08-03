from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


VARIANTS = {"smoke_free", "loose", "nominal", "narrow"}
RESOLUTION_M = 0.02


def _voxel(x: float, y: float, z: float) -> tuple[float, float, float]:
    return tuple(round(round(v / RESOLUTION_M) * RESOLUTION_M, 6) for v in (x, y, z))


def _segment(points: set[tuple[float, float, float]], start, end, radius: float) -> None:
    length = math.dist(start, end)
    steps = max(1, math.ceil(length / RESOLUTION_M))
    rings = max(1, math.ceil(radius / RESOLUTION_M))
    for i in range(steps + 1):
        u = i / steps
        center = tuple(start[k] + u * (end[k] - start[k]) for k in range(3))
        for ix in range(-rings, rings + 1):
            for iy in range(-rings, rings + 1):
                for iz in range(-rings, rings + 1):
                    offset = (ix * RESOLUTION_M, iy * RESOLUTION_M, iz * RESOLUTION_M)
                    if math.dist((0.0, 0.0, 0.0), offset) <= radius:
                        points.add(_voxel(*(center[k] + offset[k] for k in range(3))))


def _official_target_proxy(points: set[tuple[float, float, float]]) -> None:
    # Matches the already-audited desk/platform proxy used by the official
    # mode-2 runner: 0.6 m square, object z=0.62, object_height=0.1.
    for ix in range(-15, 15):
        for iy in range(-15, 15):
            x, y = ix * RESOLUTION_M, iy * RESOLUTION_M
            if max(abs(x), abs(y)) <= 0.03:
                continue
            points.add(_voxel(x, y, 0.57))
            for iz in range(1, 29):
                points.add(_voxel(x, y, iz * RESOLUTION_M))


def build_points(variant: str) -> list[tuple[float, float, float]]:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant: {variant}")
    points: set[tuple[float, float, float]] = set()
    _official_target_proxy(points)
    if variant == "smoke_free":
        # No crossarm obstacle; retain the official target proxy so SFC has a
        # finite local obstacle set and the PointCloud2 is non-empty.
        return sorted(points)
    beam_z = {"loose": 1.10, "nominal": 1.32, "narrow": 1.48}[variant]
    beam_radius = {"loose": 0.04, "nominal": 0.05, "narrow": 0.12}[variant]
    # Main crossarm, pole, and one adjacent obstacle are intentionally retained
    # in every non-free scene; only the clearance boundary changes by variant.
    _segment(points, (0.0, -1.20, beam_z), (0.0, 1.20, beam_z), beam_radius)
    _segment(points, (0.0, 0.0, 0.15), (0.0, 0.0, beam_z), 0.06)
    _segment(points, (0.0, 0.62, 0.35), (0.0, 0.62, 1.65), 0.045)
    return sorted(points)


def manifest(variant: str) -> dict[str, object]:
    points = build_points(variant)
    raw = "\n".join(f"{x:.6f},{y:.6f},{z:.6f}" for x, y, z in points).encode()
    aabb = None
    if points:
        aabb = {"min": [min(p[i] for p in points) for i in range(3)], "max": [max(p[i] for p in points) for i in range(3)]}
    return {
        "scene": variant,
        "frame_id": "world",
        "topic": "/global_map",
        "resolution_m": RESOLUTION_M,
        "point_count": len(points),
        "aabb_m": aabb,
        "points_sha256": hashlib.sha256(raw).hexdigest(),
        "obstacle_contract": "crossarm_main_beam_plus_pole_plus_adjacent_proxy",
        "nominal_clearance_gate_m": 0.010,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=sorted(VARIANTS), default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/evidence/S2-R2/maps"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    variants = [args.variant] if args.variant else sorted(VARIANTS)
    for variant in variants:
        (args.output_dir / f"{variant}.json").write_text(json.dumps(manifest(variant), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
