from __future__ import annotations

import hashlib
from collections.abc import Sequence

import pytest

from planner_bridge.scenes.generate_s2_r2_crossarm_map import build_point_groups, build_points, manifest


NOMINAL_POINT_COUNT = 29_984
NOMINAL_POINTS_SHA256 = "79eab0b6a5f4aadcba6469ef3b0c1c50efb449ef58a53c1916edfc658c299145"
POINT_GROUP_NAMES = ("TargetProxy", "MainBeam", "Column", "AdjacentObstacle")
POINT_GROUP_CONTRACT = {
    "TargetProxy": (24_948, "c31272dfe9c8c9e6f4d4ef286c25b733e6afc4103a9508bfd78bd644887a42f5"),
    "MainBeam": (2_601, "4f243e9edd467320bfe733301ec2ecec8e6b0d554ea5b5e925a9b4c982cc9d80"),
    "Column": (1_802, "48633f46ce4ba42f8e61ffcaa62c08f9508ab1e31fa08e3eb4d7bed16b862b6f"),
    "AdjacentObstacle": (1_269, "d7738ec90ebfbaee5b1f51cf14d613a9ade882d3655f7f5846ad06594d880aae"),
}


def _points_sha256(points: Sequence[tuple[float, float, float]]) -> str:
    raw = "\n".join(f"{x:.6f},{y:.6f},{z:.6f}" for x, y, z in points).encode()
    return hashlib.sha256(raw).hexdigest()


def test_nominal_point_groups_are_read_only_and_complete() -> None:
    groups = build_point_groups("nominal")

    assert tuple(groups) == POINT_GROUP_NAMES
    assert all(isinstance(points, tuple) and points for points in groups.values())
    with pytest.raises(TypeError):
        groups["TargetProxy"] = ()  # type: ignore[index]


def test_nominal_point_group_membership_is_frozen() -> None:
    groups = build_point_groups("nominal")

    for name, (expected_count, expected_sha256) in POINT_GROUP_CONTRACT.items():
        assert len(groups[name]) == expected_count
        assert _points_sha256(groups[name]) == expected_sha256


def test_nominal_point_group_union_has_no_added_or_removed_points() -> None:
    original = set(build_points("nominal"))
    grouped_union = set().union(*(set(points) for points in build_point_groups("nominal").values()))

    assert grouped_union - original == set()
    assert original - grouped_union == set()
    assert grouped_union == original


def test_nominal_point_cloud_count_and_sha_remain_frozen() -> None:
    points = build_points("nominal")

    assert len(points) == NOMINAL_POINT_COUNT
    assert _points_sha256(points) == NOMINAL_POINTS_SHA256
    assert manifest("nominal")["point_count"] == NOMINAL_POINT_COUNT
    assert manifest("nominal")["points_sha256"] == NOMINAL_POINTS_SHA256


def test_point_groups_reject_non_nominal_variants() -> None:
    with pytest.raises(ValueError, match="only for the nominal variant"):
        build_point_groups("loose")
    with pytest.raises(ValueError, match="unknown variant"):
        build_point_groups("unknown")
