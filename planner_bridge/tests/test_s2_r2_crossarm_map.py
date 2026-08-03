from planner_bridge.scenes.generate_s2_r2_crossarm_map import build_points, manifest


def test_four_map_variants_are_deterministic():
    for variant in ("smoke_free", "loose", "nominal", "narrow"):
        assert build_points(variant) == build_points(variant)
        assert manifest(variant)["frame_id"] == "world"


def test_narrow_has_more_obstacle_voxels_than_smoke_free():
    assert len(build_points("narrow")) > len(build_points("smoke_free"))
