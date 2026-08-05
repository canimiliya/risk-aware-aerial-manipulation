from __future__ import annotations

import math

import numpy as np
from scipy.spatial import cKDTree

from planner_bridge.scenes.generate_s2_r2_crossarm_map import build_points


BODY_RADIUS_M = 0.20
ROTOR_RADIUS_M = 0.25
LINK_RADIUS_M = 0.010
PLATFORM_RADIUS_M = 0.025
END_EFFECTOR_RADIUS_M = 0.025


def _rotz(angle: float) -> np.ndarray:
    return np.array([[math.cos(angle), -math.sin(angle), 0.0], [math.sin(angle), math.cos(angle), 0.0], [0.0, 0.0, 1.0]])


T_B_A0 = np.eye(4)
T_B_A0[:3, :3] = _rotz(math.pi / 2.0)
T_B_A0[:3, 3] = [-0.04, 0.0, 0.0]

# A0/body rotor centers are provisional because the official arm.xacro names
# drone.dae but does not expose rotor centers/radii.
ROTOR_CENTERS_B = np.asarray([[0.17, 0.17, 0.05], [-0.17, 0.17, 0.05], [-0.17, -0.17, 0.05], [0.17, -0.17, 0.05]])


def _segment_samples(start: np.ndarray, end: np.ndarray, count: int = 9) -> np.ndarray:
    return np.linspace(start, end, count)


def _disk_samples(center: np.ndarray, normal: np.ndarray, radius: float) -> np.ndarray:
    normal = normal / np.linalg.norm(normal)
    tangent = np.cross(normal, np.array([0.0, 0.0, 1.0]))
    if np.linalg.norm(tangent) < 1e-8:
        tangent = np.cross(normal, np.array([0.0, 1.0, 0.0]))
    tangent /= np.linalg.norm(tangent)
    bitangent = np.cross(normal, tangent)
    points = [center]
    for frac in (0.5, 1.0):
        for angle in np.linspace(0.0, 2.0 * math.pi, 9)[:-1]:
            points.append(center + frac * radius * (math.cos(angle) * tangent + math.sin(angle) * bitangent))
    return np.asarray(points)


def _clearance(tree: cKDTree, samples: np.ndarray, radius: float) -> float:
    return float(np.min(tree.query(samples, k=1)[0]) - radius)


def point_to_aabb_distance(point: np.ndarray, center: np.ndarray, size: np.ndarray) -> float:
    """Analytic Euclidean distance from a point to an axis-aligned scene AABB."""
    point = np.asarray(point, dtype=float)
    center = np.asarray(center, dtype=float)
    size = np.asarray(size, dtype=float)
    if point.shape != (3,) or center.shape != (3,) or size.shape != (3,) or np.any(size < 0.0):
        raise ValueError("point, center and size must be finite 3-vectors with non-negative size")
    lower = center - 0.5 * size
    upper = center + 0.5 * size
    delta = np.maximum(np.maximum(lower - point, 0.0), point - upper)
    return float(np.linalg.norm(delta))


def sampled_proxy_aabb_clearance(component: tuple[np.ndarray, float], center: np.ndarray, size: np.ndarray) -> dict[str, object]:
    """Return exact nearest-sample data for one frozen sample set and one AABB."""
    points, radius = component
    distances = np.asarray([point_to_aabb_distance(point, center, size) for point in points], dtype=float)
    index = int(np.argmin(distances))
    return {
        "distance_m": float(distances[index]),
        "clearance_m": float(distances[index] - radius),
        "nearest_sample_index": index,
        "nearest_sample_point_m": np.asarray(points[index], dtype=float).tolist(),
        "component_radius_m": float(radius),
    }


def component_sample_sets(p_wb: np.ndarray, R_wb: np.ndarray, arm_point: np.ndarray, joint_points: dict, radii_scale: float = 1.0) -> dict[str, tuple[np.ndarray, float]]:
    def world_body(point: np.ndarray) -> np.ndarray:
        return p_wb + R_wb @ point

    samples: dict[str, tuple[np.ndarray, float]] = {"body": (np.asarray([p_wb]), BODY_RADIUS_M * radii_scale)}
    rotor_values = []
    rotor_normal = R_wb[:, 2]
    for i, center_b in enumerate(ROTOR_CENTERS_B):
        samples[f"rotor_{i+1}"] = (_disk_samples(world_body(center_b), rotor_normal, ROTOR_RADIUS_M * radii_scale), 0.0)
    A, B = joint_points["A"], joint_points["B"]
    for i in range(3):
        samples_a0 = _segment_samples(A[i], B[i])
        samples_b = (T_B_A0[:3, :3] @ samples_a0.T).T + T_B_A0[:3, 3]
        samples[f"upper_arm_{i+1}"] = (np.asarray([world_body(x) for x in samples_b]), LINK_RADIUS_M * radii_scale)
    for i in range(3):
        for side in ("left", "right"):
            start = joint_points[f"B_{side}"][i]
            end = joint_points[f"C_{side}"][i]
            samples_a0 = _segment_samples(start, end)
            samples_b = (T_B_A0[:3, :3] @ samples_a0.T).T + T_B_A0[:3, 3]
            samples[f"lower_arm_{i+1}_{side}"] = (np.asarray([world_body(x) for x in samples_b]), LINK_RADIUS_M * radii_scale)
    end_b = world_body(T_B_A0[:3, :3] @ np.asarray(arm_point) + T_B_A0[:3, 3])
    samples["moving_platform"] = (np.asarray([end_b]), PLATFORM_RADIUS_M * radii_scale)
    samples["end_effector"] = (np.asarray([end_b]), END_EFFECTOR_RADIUS_M * radii_scale)
    return samples


def component_clearances(p_wb: np.ndarray, R_wb: np.ndarray, arm_point: np.ndarray, joint_points: dict, obstacle_tree: cKDTree, radii_scale: float = 1.0) -> dict[str, float]:
    return {name: _clearance(obstacle_tree, points, radius) for name, (points, radius) in component_sample_sets(p_wb, R_wb, arm_point, joint_points, radii_scale).items()}


def closest_component_obstacle(component: tuple[np.ndarray, float], obstacle_tree: cKDTree) -> tuple[float, np.ndarray, np.ndarray]:
    points, radius = component
    distances, indices = obstacle_tree.query(points, k=1)
    idx = int(np.argmin(distances))
    obstacle = np.asarray(obstacle_tree.data[int(indices[idx])], dtype=float)
    return float(distances[idx] - radius), obstacle, np.asarray(points[idx], dtype=float)


def obstacle_tree(variant: str) -> cKDTree:
    if variant == "nominal_repeat":
        variant = "nominal"
    return cKDTree(np.asarray(build_points(variant), dtype=float))
