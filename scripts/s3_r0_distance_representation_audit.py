"""Pure-Python S3-R0 distance representation and conservatism audit."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from planner_bridge.execution.full_body_proxy import component_sample_sets, obstacle_tree, sampled_proxy_aabb_clearance
from planner_bridge.execution.official_delta_kinematics import official_fk_joint_state, official_joint_points
from planner_bridge.protocol.frames import rotation_from_quaternion_wxyz
from planner_bridge.scenes.generate_s2_r2_crossarm_map import build_point_groups, build_points, manifest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/S3-R0"
OUT = EVIDENCE / "distance_representation"
RUNS = ("isaac_playback_nominal_1_r5_grid", "isaac_playback_nominal_2_r5", "isaac_playback_nominal_3_r5", "isaac_playback_nominal_repeat_r5")
GROUPS = ("TargetProxy", "MainBeam", "Column", "AdjacentObstacle")
COMPONENTS = ("body", "rotor_1", "rotor_2", "rotor_3", "rotor_4", "upper_arm_1", "upper_arm_2", "upper_arm_3", "lower_arm_1_left", "lower_arm_1_right", "lower_arm_2_left", "lower_arm_2_right", "lower_arm_3_left", "lower_arm_3_right", "moving_platform", "end_effector")
GATE_M = 0.010
REPLAY_GATE_M = 0.002
ORDER_TOLERANCE_M = 1e-9
BOXES = {
    "MainBeam": (np.array([0.0, 0.0, 1.32]), np.array([0.12, 2.52, 0.12])),
    "Column": (np.array([0.0, 0.0, 0.735]), np.array([0.12, 0.12, 1.29])),
    "AdjacentObstacle": (np.array([0.0, 0.62, 0.995]), np.array([0.12, 0.12, 1.41])),
    "TargetProxy": (np.array([0.0, 0.0, 0.295]), np.array([0.60, 0.60, 0.55])),
}


def _ready(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return value.item()
    if isinstance(value, dict):
        return {k: _ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_ready(v) for v in value]
    return value


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(_ready(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha(points: list[tuple[float, float, float]]) -> str:
    raw = "\n".join(f"{x:.6f},{y:.6f},{z:.6f}" for x, y, z in points).encode()
    return hashlib.sha256(raw).hexdigest()


def _states(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def containment_proof() -> dict[str, Any]:
    raw_groups = build_point_groups("nominal")
    groups = {name: [tuple(float(v) for v in point) for point in raw_groups[name]] for name in GROUPS}
    original = sorted(tuple(float(v) for v in p) for p in build_points("nominal"))
    union = sorted({p for values in groups.values() for p in values})
    original_sha = manifest("nominal")["points_sha256"]
    rows = {}
    for name in GROUPS:
        center, size = BOXES[name]
        lower, upper = center - size / 2.0, center + size / 2.0
        values = np.asarray(groups[name], dtype=float)
        outside = np.linalg.norm(np.maximum(np.maximum(lower - values, 0.0), values - upper), axis=1)
        margins = np.min(np.minimum(values - lower, upper - values), axis=1)
        outside_indices = np.flatnonzero(outside > ORDER_TOLERANCE_M)
        cloud_min, cloud_max = np.min(values, axis=0), np.max(values, axis=0)
        rows[name] = {
            "point_count": len(values), "s3_aabb_center_m": center, "s3_aabb_size_m": size,
            "s3_aabb_min_m": lower, "s3_aabb_max_m": upper,
            "s2_point_cloud_min_m": cloud_min, "s2_point_cloud_max_m": cloud_max,
            "aabb_expansion_relative_to_point_cloud_m": size - (cloud_max - cloud_min),
            "outside_count": int(np.count_nonzero(outside > ORDER_TOLERANCE_M)),
            "max_outside_distance_m": float(np.max(outside)) if len(outside) else 0.0,
            "outside_examples": [{"point_m": values[index], "outside_distance_m": outside[index]} for index in outside_indices[:10]],
            "min_margin_to_aabb_boundary_m": float(np.min(margins)) if len(margins) else 0.0,
        }
        rows[name]["contained"] = rows[name]["outside_count"] == 0 and rows[name]["max_outside_distance_m"] <= ORDER_TOLERANCE_M
    union_sha = _sha(union)
    result = {
        "decision": "PASS" if union == original and union_sha == original_sha and all(row["contained"] for row in rows.values()) else "FAIL",
        "groups": rows, "group_names": list(GROUPS), "union_point_count": len(union), "original_point_count": len(original),
        "union_equals_build_points": union == original, "original_points_sha256": original_sha, "union_points_sha256": union_sha,
        "point_cloud_sha_unchanged": union_sha == original_sha,
        "outside_count": sum(row["outside_count"] for row in rows.values()),
        "max_outside_distance_m": max(row["max_outside_distance_m"] for row in rows.values()),
        "conservative_envelope_pass": all(row["contained"] for row in rows.values()),
        "quantification_only": {"voxel_resolution_m": 0.02, "interpretation": "AABB fills cylinder corners, voxel gaps, and the TargetProxy central exclusion region; these are representation effects, not equivalence claims."},
    }
    return result


def distance_run(name: str) -> dict[str, Any]:
    states = _states(EVIDENCE / f"{name}.state.jsonl")
    tree = obstacle_tree("nominal")
    n, c = len(states), len(COMPONENTS)
    times = np.empty(n); g1 = np.empty((n, c)); g2 = np.empty((n, c)); obstacles: list[list[str]] = []; g2_points: list[list[list[float]]] = []
    for i, state in enumerate(states):
        times[i] = state["reference_time_s"]
        q = np.asarray(state["q_rad"], dtype=float)
        base = np.asarray(state["base_position_WB_m"], dtype=float)
        rotation = rotation_from_quaternion_wxyz(np.asarray(state["base_quaternion_WB_wxyz"], dtype=float))
        arm = official_fk_joint_state(q)
        samples = component_sample_sets(base, rotation, arm, official_joint_points(arm, q))
        obstacle_row, point_row = [], []
        for j, component in enumerate(COMPONENTS):
            sample_set = samples[component]
            candidates = {obstacle: sampled_proxy_aabb_clearance(sample_set, center, size) for obstacle, (center, size) in BOXES.items()}
            obstacle, best = min(candidates.items(), key=lambda item: item[1]["clearance_m"])
            g1[i, j] = best["clearance_m"]; obstacle_row.append(obstacle)
            points, radius = sample_set
            distances, indices = tree.query(points, k=1); sample_index = int(np.argmin(distances))
            g2[i, j] = distances[sample_index] - radius
            point_row.append(np.asarray(tree.data[int(indices[sample_index])], dtype=float).tolist())
        obstacles.append(obstacle_row); g2_points.append(point_row)
    gap = g1 - g2
    historical = json.loads((EVIDENCE / f"{name}.json").read_text(encoding="utf-8"))["g3_historical_s2_r6_nominal_2000hz"]["min_clearance_m"]
    minima = {}
    for j, component in enumerate(COMPONENTS):
        i1, i2 = int(np.argmin(g1[:, j])), int(np.argmin(g2[:, j]))
        minima[component] = {"g1_min_clearance_m": g1[i1, j], "g1_frame": i1, "g1_time_s": times[i1], "g1_obstacle": obstacles[i1][j], "g2_min_clearance_m": g2[i2, j], "g2_frame": i2, "g2_time_s": times[i2], "g2_nearest_point_m": g2_points[i2][j], "g1_gate_pass": bool(np.min(g1[:, j]) >= GATE_M), "framewise_conservative_order_pass": bool(np.all(gap[:, j] <= ORDER_TOLERANCE_M))}
    i1, j1 = np.unravel_index(np.argmin(g1), g1.shape); i2, j2 = np.unravel_index(np.argmin(g2), g2.shape)
    return {"run": name, "state_count": n, "times_s": times, "g1_m": g1, "g2_m": g2, "gap_g1_minus_g2_m": gap, "g1_obstacles": obstacles, "g2_points": g2_points, "component_minima": minima, "g1_min_clearance_m": g1[i1,j1], "g1_dangerous_component": COMPONENTS[j1], "g1_dangerous_obstacle": obstacles[i1][j1], "g1_dangerous_frame": i1, "g1_dangerous_time_s": times[i1], "g2_min_clearance_m": g2[i2,j2], "g2_dangerous_component": COMPONENTS[j2], "g2_dangerous_frame": i2, "g2_dangerous_time_s": times[i2], "g2_nearest_point_m": g2_points[i2][j2], "g3_historical_min_clearance_m": historical, "state_replay_s2_clearance_delta_m": abs(g2[i2,j2] - historical), "g1_gate_pass": bool(np.min(g1) >= GATE_M), "framewise_conservative_order_pass": bool(np.all(gap <= ORDER_TOLERANCE_M)), "max_g1_minus_g2_m": float(np.max(gap)), "min_g2_minus_g1_m": float(np.min(-gap)), "geometry_representation_conservatism_m": float(g2[i2,j2] - g1[i1,j1])}


def run(output_dir: Path = OUT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    containment = containment_proof()
    _write(output_dir / "obstacle_correspondence.json", {"boxes": {k: {"center_m": center, "size_m": size} for k, (center, size) in BOXES.items()}})
    _write(output_dir / "s2_points_inside_s3_aabbs.json", containment)
    runs = [distance_run(name) for name in RUNS]
    g1 = np.stack([run["g1_m"] for run in runs]); g2 = np.stack([run["g2_m"] for run in runs]); gap = np.stack([run["gap_g1_minus_g2_m"] for run in runs]); times = np.stack([run["times_s"] for run in runs])
    np.savez_compressed(output_dir / "framewise_g1_g2.npz", times_s=times, g1_m=g1, g2_m=g2, gap_g1_minus_g2_m=gap)
    _write(output_dir / "framewise_g1_g2.json", {"runs": list(RUNS), "components": list(COMPONENTS), "shape": list(g1.shape), "definitions": {"G1": "Isaac AABB sampled-proxy clearance", "G2": "S2 nominal point-cloud sampled-proxy clearance", "G3": "historical S2-R6 nominal 2000 Hz clearance", "gap": "G1-G2 representation diagnostic, not a hard gate"}, "all_rows_pass": bool(np.all(gap <= ORDER_TOLERANCE_M)), "max_g1_minus_g2_m": float(np.max(gap)), "min_g2_minus_g1_m": float(np.min(-gap))})
    _write(output_dir / "per_component_minima.json", {run["run"]: run["component_minima"] for run in runs})
    g1_global, g2_global = min(runs, key=lambda run: run["g1_min_clearance_m"]), min(runs, key=lambda run: run["g2_min_clearance_m"])
    replay_max = max(run["state_replay_s2_clearance_delta_m"] for run in runs)
    summary = {"decision": "PASS" if containment["decision"] == "PASS" and all(run["g1_gate_pass"] and run["framewise_conservative_order_pass"] for run in runs) and replay_max <= REPLAY_GATE_M else "FAIL", "definitions": {"G1": "Isaac scene AABB sampled-proxy clearance", "G2": "S2 nominal point-cloud sampled-proxy clearance", "G3": "historical S2-R6 nominal 2000 Hz clearance", "geometry_representation_conservatism_m": "G2-G1; positive means AABB is more conservative", "state_replay_s2_clearance_delta_m": "abs(G2-G3), the only S2 replay delta"}, "old_gate_retired": {"name": "G1-G2 <= 0.002 m", "reason": "AABB envelope and voxelized point-cloud proxy are different geometries; numerical equivalence is invalid."}, "contracts": {"isaac_aabb_clearance_gate": all(run["g1_gate_pass"] for run in runs), "state_replay_s2_clearance_delta": replay_max <= REPLAY_GATE_M, "s2_points_contained_by_isaac_aabbs": containment["conservative_envelope_pass"], "framewise_conservative_order": all(run["framewise_conservative_order_pass"] for run in runs), "geometry_representation_delta_reported": True}, "g1": {"min_clearance_m": g1_global["g1_min_clearance_m"], "dangerous_component": g1_global["g1_dangerous_component"], "dangerous_obstacle": g1_global["g1_dangerous_obstacle"], "dangerous_time_s": g1_global["g1_dangerous_time_s"]}, "g2": {"min_clearance_m": g2_global["g2_min_clearance_m"], "dangerous_component": g2_global["g2_dangerous_component"], "dangerous_time_s": g2_global["g2_dangerous_time_s"], "nearest_point_m": g2_global["g2_nearest_point_m"]}, "g3": {"min_clearance_m": g2_global["g3_historical_min_clearance_m"], "dangerous_component": "rotor_4"}, "geometry_representation_conservatism_m": g2_global["geometry_representation_conservatism_m"], "state_replay_s2_clearance_delta_m_max": replay_max, "runs": [{k: v for k, v in run.items() if k not in {"times_s", "g1_m", "g2_m", "gap_g1_minus_g2_m", "g1_obstacles", "g2_points"}} for run in runs], "s2_point_containment": containment}
    _write(output_dir / "formal_distance_summary.json", summary)
    report = f"""# S3-R0 distance representation report

The former `|G1-G2| <= 0.002 m` gate is retired: G1 is an Isaac AABB-envelope
distance and G2 is a frozen S2 voxel/point-cloud distance. The diagnostic
`G1-G2` remains recorded; `geometry_representation_conservatism_m = G2-G1`
is positive when the AABB representation is more conservative.

- Point/AABB containment: **{containment['decision']}**, outside count `{containment['outside_count']}`, max outside distance `{containment['max_outside_distance_m']:.17g} m`.
- Point-cloud SHA unchanged: **{containment['point_cloud_sha_unchanged']}**.
- G1 minimum: `{summary['g1']['min_clearance_m']:.17g} m`, `{summary['g1']['dangerous_component']}` vs `{summary['g1']['dangerous_obstacle']}` at `{summary['g1']['dangerous_time_s']:.17g} s`.
- G2 minimum: `{summary['g2']['min_clearance_m']:.17g} m`, `{summary['g2']['dangerous_component']}` at `{summary['g2']['dangerous_time_s']:.17g} s`.
- G3 historical minimum: `{summary['g3']['min_clearance_m']:.17g} m`, `rotor_4`.
- Max `|G2-G3|`: `{replay_max:.17g} m`; max framewise `G1-G2`: `{float(np.max(gap)):.17g} m`.
- Representation effects are quantified per group in `s2_points_inside_s3_aabbs.json`; no AABB/point-cloud equivalence is claimed.

Overall decision: **{summary['decision']}**.
"""
    (output_dir / "representation_report.md").write_text(report, encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output-dir", type=Path, default=OUT); args = parser.parse_args()
    result = run(args.output_dir); print(json.dumps(_ready(result), ensure_ascii=False, indent=2)); return 0 if result["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
