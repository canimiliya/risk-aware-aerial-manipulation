from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from planner_bridge.scenes.generate_s2_r2_crossarm_map import build_point_groups, build_points, manifest
from planner_bridge.scenes.s3_r0_scene_contract import SCENE_AABB_FRAME, SCENE_AABBS, scene_aabb_contract_payload
from scripts import s3_r0_distance_representation_audit as distance_audit
from scripts import s3_r0_reference_playback as reference_playback


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


def test_canonical_scene_aabbs_are_immutable_world_frame_contract() -> None:
    assert SCENE_AABB_FRAME == "world"
    assert tuple(SCENE_AABBS) == POINT_GROUP_NAMES

    column = SCENE_AABBS["Column"]
    assert column.center_m == (0.0, 0.0, 0.73)
    assert column.size_m == (0.12, 0.12, 1.30)
    np.testing.assert_allclose(column.min_m, (-0.06, -0.06, 0.08), rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(column.max_m, (0.06, 0.06, 1.38), rtol=0.0, atol=1e-15)

    with pytest.raises(TypeError):
        SCENE_AABBS["Column"] = column  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        column.center_m = (0.0, 0.0, 0.0)  # type: ignore[misc]


@pytest.mark.parametrize("name", POINT_GROUP_NAMES)
def test_each_s2_point_group_is_contained_by_its_canonical_aabb(name: str) -> None:
    points = np.asarray(build_point_groups("nominal")[name], dtype=float)
    aabb = SCENE_AABBS[name]
    lower = np.asarray(aabb.min_m, dtype=float)
    upper = np.asarray(aabb.max_m, dtype=float)
    outside = np.linalg.norm(np.maximum(np.maximum(lower - points, 0.0), points - upper), axis=1)

    assert int(np.count_nonzero(outside > 1e-9)) == 0
    assert float(np.max(outside)) <= 1e-9


def test_playback_audit_and_evidence_payload_share_canonical_aabbs() -> None:
    assert reference_playback._scene_boxes() is SCENE_AABBS
    assert distance_audit.SCENE_AABBS is SCENE_AABBS
    assert distance_audit.GROUPS == tuple(SCENE_AABBS)

    payload = scene_aabb_contract_payload()
    assert payload["coordinate_frame"] == "world"
    assert payload["boxes"] == {name: aabb.as_dict() for name, aabb in SCENE_AABBS.items()}


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
