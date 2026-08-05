"""Canonical S3-R0 obstacle AABBs in the world coordinate frame.

This module is the single source of truth for scene geometry consumed by the
Isaac playback and the pure-Python distance audit.  Values are expressed in
metres and are immutable after import.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Mapping, TypeAlias


Vector3: TypeAlias = tuple[float, float, float]
SCENE_AABB_FRAME: Final = "world"


def _vector3(values: Vector3, field: str) -> Vector3:
    converted = tuple(float(value) for value in values)
    if len(converted) != 3 or not all(math.isfinite(value) for value in converted):
        raise ValueError(f"{field} must be a finite 3-vector")
    return converted  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class SceneAABB:
    """Immutable axis-aligned box represented by world-frame center and size."""

    center_m: Vector3
    size_m: Vector3

    def __post_init__(self) -> None:
        center = _vector3(self.center_m, "center_m")
        size = _vector3(self.size_m, "size_m")
        if any(value <= 0.0 for value in size):
            raise ValueError("size_m must be strictly positive on every axis")
        object.__setattr__(self, "center_m", center)
        object.__setattr__(self, "size_m", size)

    @property
    def min_m(self) -> Vector3:
        return (
            self.center_m[0] - self.size_m[0] / 2.0,
            self.center_m[1] - self.size_m[1] / 2.0,
            self.center_m[2] - self.size_m[2] / 2.0,
        )

    @property
    def max_m(self) -> Vector3:
        return (
            self.center_m[0] + self.size_m[0] / 2.0,
            self.center_m[1] + self.size_m[1] / 2.0,
            self.center_m[2] + self.size_m[2] / 2.0,
        )

    def as_dict(self) -> dict[str, list[float]]:
        return {
            "center_m": list(self.center_m),
            "size_m": list(self.size_m),
            "min_m": list(self.min_m),
            "max_m": list(self.max_m),
        }


SCENE_AABBS: Final[Mapping[str, SceneAABB]] = MappingProxyType(
    {
        "TargetProxy": SceneAABB((0.0, 0.0, 0.295), (0.60, 0.60, 0.55)),
        "MainBeam": SceneAABB((0.0, 0.0, 1.32), (0.12, 2.52, 0.12)),
        "Column": SceneAABB((0.0, 0.0, 0.73), (0.12, 0.12, 1.30)),
        "AdjacentObstacle": SceneAABB((0.0, 0.62, 0.995), (0.12, 0.12, 1.41)),
    }
)
SCENE_AABB_KEYS: Final = tuple(SCENE_AABBS)

_PREVIOUS_COLUMN_AABB: Final = SceneAABB((0.0, 0.0, 0.735), (0.12, 0.12, 1.29))
_COLUMN_CHANGE_RATIONALE: Final = (
    "Minimal lower-z expansion to contain the frozen S2 Column point cloud "
    "while preserving z_max=1.38 m; no empirical padding was added."
)


def scene_aabb_contract_payload() -> dict[str, object]:
    """Return a JSON-ready description generated from the canonical AABBs."""

    return {
        "contract": "S3-R0-canonical-scene-aabbs-v1",
        "coordinate_frame": SCENE_AABB_FRAME,
        "units": "m",
        "boxes": {name: aabb.as_dict() for name, aabb in SCENE_AABBS.items()},
        "column_revision": {
            "old": _PREVIOUS_COLUMN_AABB.as_dict(),
            "new": SCENE_AABBS["Column"].as_dict(),
            "changed_axes": ["z"],
            "change_rationale": _COLUMN_CHANGE_RATIONALE,
        },
    }


__all__ = [
    "SCENE_AABB_FRAME",
    "SCENE_AABB_KEYS",
    "SCENE_AABBS",
    "SceneAABB",
    "scene_aabb_contract_payload",
]
