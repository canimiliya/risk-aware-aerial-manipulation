from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .clearance_geometry import Box, clearance_for_links, proxy_clearance
from .delta_arm_model import DeltaArmModel
from .evaluate_task_poses import POSES, make_boxes
from .jacobian_metrics import jacobian_metrics


def quintic_blend(u: float) -> float:
    """C2 position blend with zero velocity and acceleration at both ends."""
    u = float(np.clip(u, 0.0, 1.0))
    return 10.0 * u**3 - 15.0 * u**4 + 6.0 * u**5


def interpolate_waypoints(
    waypoints: list[tuple[str, np.ndarray]],
    samples_per_segment: int,
) -> list[dict[str, object]]:
    if len(waypoints) < 2:
        raise ValueError("at least two waypoints are required")
    if samples_per_segment < 2:
        raise ValueError("samples_per_segment must be at least 2")
    trajectory: list[dict[str, object]] = []
    for segment, ((start_name, start_q), (end_name, end_q)) in enumerate(zip(waypoints, waypoints[1:])):
        us = np.linspace(0.0, 1.0, samples_per_segment)
        if segment:
            us = us[1:]
        for u in us:
            q = np.asarray(start_q, dtype=float) + quintic_blend(float(u)) * (np.asarray(end_q, dtype=float) - np.asarray(start_q, dtype=float))
            trajectory.append({
                "sample_index": len(trajectory),
                "segment": segment,
                "segment_start": start_name,
                "segment_end": end_name,
                "u": float(u),
                "q_rad": q.tolist(),
                # W->B is held at the explicit preflight reference pose. It is
                # a contract placeholder until vehicle state data is available.
                "vehicle_pose_WB": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            })
    return trajectory


def evaluate_continuous_plan(
    model: DeltaArmModel,
    scene: dict,
    trajectory: list[dict[str, object]],
    width_key: str = "nominal",
) -> dict[str, object]:
    boxes: list[Box] = make_boxes(scene, width_key)
    evaluated: list[dict[str, object]] = []
    invalid_samples: list[int] = []
    for sample in trajectory:
        q = np.asarray(sample["q_rad"], dtype=float)
        item = dict(sample)
        try:
            position = model.fk(q)
            links = model.link_points(q)
            body = proxy_clearance(np.zeros(3), boxes, scene["proxies"]["body_radius_m"])
            rotor = proxy_clearance(np.array([0.0, 0.0, scene["proxies"]["rotor_z_m"]]), boxes, scene["proxies"]["rotor_radius_m"])
            link = clearance_for_links(links, boxes)
            jacobian = jacobian_metrics(model, q)
            item.update({
                "position_A0_m": position.tolist(),
                "tool_axis_A0": [1.0, 0.0, 0.0],
                "horizontal": True,
                "joint_margin": model.normalized_joint_margin(q),
                "link_clearance_m": link,
                "body_clearance_m": body,
                "rotor_clearance_m": rotor,
                "clearance_m": min(link, body, rotor),
                "jacobian": jacobian,
                "finite": bool(np.all(np.isfinite(position)) and all(np.isfinite(value) for value in jacobian.values())),
            })
        except (ValueError, FloatingPointError) as error:
            invalid_samples.append(int(sample["sample_index"]))
            item.update({"finite": False, "error": str(error)})
        evaluated.append(item)
    valid = [item for item in evaluated if item.get("finite")]
    min_clearance = min((float(item["clearance_m"]) for item in valid), default=float("nan"))
    min_margin = min((float(item["joint_margin"]) for item in valid), default=float("nan"))
    min_sigma = min((float(item["jacobian"]["min_singular_value"]) for item in valid), default=float("nan"))
    max_condition = max((float(item["jacobian"]["condition_number"]) for item in valid), default=float("nan"))
    return {
        "scene_variant": width_key,
        "sample_count": len(evaluated),
        "invalid_sample_count": len(invalid_samples),
        "invalid_sample_indices": invalid_samples,
        "samples": evaluated,
        "metrics": {
            "min_clearance_m": min_clearance,
            "min_joint_margin": min_margin,
            "min_jacobian_min_singular_value": min_sigma,
            "max_jacobian_condition_number": max_condition,
        },
    }


def plan_from_p0_p6(
    scene_path: Path,
    output_path: Path,
    samples_per_segment: int = 101,
    width_key: str = "nominal",
) -> dict[str, object]:
    import yaml

    scene = yaml.safe_load(scene_path.read_text(encoding="utf-8"))
    model = DeltaArmModel()
    waypoints = [(name, q) for name, q, _ in POSES]
    trajectory = interpolate_waypoints(waypoints, samples_per_segment)
    result = evaluate_continuous_plan(model, scene, trajectory, width_key)
    result["planner_contract"] = "S2-R1_CONTINUOUS_WHOLE_BODY_PREPLANNING"
    result["vehicle_state_mode"] = "FIXED_WB_REFERENCE_PROVISIONAL"
    result["waypoint_names"] = [name for name, _, _ in POSES]
    result["samples_per_segment"] = samples_per_segment
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
