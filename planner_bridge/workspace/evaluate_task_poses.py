from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .clearance_geometry import Box, clearance_for_links, proxy_clearance
from .delta_arm_model import DeltaArmModel
from .jacobian_metrics import jacobian_metrics


POSES = [
    ("P0", np.array([0.00, 0.00, 0.00]), "safe initial"),
    ("P1", np.array([0.10, 0.08, 0.08]), "outside approach"),
    ("P2", np.array([0.18, 0.12, 0.12]), "horizontal insertion start"),
    ("P3", np.array([0.24, 0.16, 0.16]), "grasp pose"),
    ("P4", np.array([0.30, 0.16, 0.16]), "straight pull-out end"),
    ("P5", np.array([0.26, 0.12, 0.13]), "rebound suppression buffer"),
    ("P6", np.array([0.16, 0.08, 0.10]), "loaded retreat"),
]


def make_boxes(scene: dict, width_key: str) -> list[Box]:
    values = scene["width_variants"][width_key]
    return [
        Box("crossarm_main_beam", np.asarray(values["main_beam_center"], dtype=float), np.asarray(values["main_beam_size"], dtype=float)),
        Box("nearby_obstacle", np.asarray(values["obstacle_center"], dtype=float), np.asarray(values["obstacle_size"], dtype=float)),
    ]


def evaluate(model: DeltaArmModel, scene: dict, width_key: str, horizontal_tolerance: float, margin_threshold: float, clearance_threshold: float) -> dict:
    boxes = make_boxes(scene, width_key)
    candidates = []
    for name, q, meaning in POSES:
        try:
            position = model.fk(q)
            links = model.link_points(q)
            clearance = clearance_for_links(links, boxes)
            body_clearance = proxy_clearance(np.zeros(3), boxes, scene["proxies"]["body_radius_m"])
            rotor_clearance = proxy_clearance(np.array([0.0, 0.0, scene["proxies"]["rotor_z_m"]]), boxes, scene["proxies"]["rotor_radius_m"])
            metrics = jacobian_metrics(model, q)
            margin = model.normalized_joint_margin(q)
            tool_axis = np.array([1.0, 0.0, 0.0])
            horizontal = abs(float(tool_axis[2])) <= horizontal_tolerance
            feasible = bool(horizontal and margin >= margin_threshold and min(clearance, body_clearance, rotor_clearance) >= clearance_threshold and bool(np.all(np.isfinite(position))))
            candidates.append({"pose": name, "meaning": meaning, "q_rad": q.tolist(), "position_A0_m": position.tolist(), "tool_axis_A0": tool_axis.tolist(), "horizontal": bool(horizontal), "joint_margin": margin, "link_clearance_m": clearance, "body_clearance_m": body_clearance, "rotor_clearance_m": rotor_clearance, "jacobian": metrics, "feasible": feasible})
        except ValueError as error:
            candidates.append({"pose": name, "meaning": meaning, "q_rad": q.tolist(), "feasible": False, "error": str(error)})
    return {"variant": width_key, "thresholds": {"horizontal_tolerance": horizontal_tolerance, "joint_margin": margin_threshold, "clearance_m": clearance_threshold}, "poses": candidates, "feasible_count": sum(item.get("feasible", False) for item in candidates)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import yaml
    scene = yaml.safe_load(args.scene.read_text(encoding="utf-8"))
    model = DeltaArmModel()
    results = {variant: evaluate(model, scene, variant, gate["horizontal_tolerance"], gate["joint_margin"], gate["clearance_m"]) for variant, gate in scene["gates"].items()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({variant: item["feasible_count"] for variant, item in results.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
