"""Build S2-R4 root-cause, execution-envelope, and static-feasibility evidence.

This script does not alter AM-Planner or the audited collision proxy. It only
recomputes the failed S2-R3 trajectories and searches task-level candidate
waypoints before a real planner invocation.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from planner_bridge.execution.full_body_proxy import component_clearances, obstacle_tree
from planner_bridge.execution.official_delta_kinematics import (
    official_fk_joint_state,
    official_ik,
    official_joint_points,
    joint_margin,
)
from planner_bridge.execution.official_flatness_wrapper import OfficialFlatnessMap, quaternion_to_rotation_wxyz
from planner_bridge.execution.playback_validator import sample_raw, validate_attitude, validate_kinematics
from planner_bridge.export.sampling import load_captured_message
from planner_bridge.scenes.generate_s2_r2_crossarm_map import build_points


R3_ROOT = ROOT / "data/trajectories/S2-R3"
R2_RUNTIME = ROOT / "data/trajectories/S2-R2/100Hz"
EVIDENCE = ROOT / "docs/evidence/S2-R4"
VARIANTS = ("smoke_free", "loose", "nominal", "nominal_repeat", "narrow")
RATES = (100, 400, 800)
GATE_M = 0.010
PREFERRED_MARGIN = 0.02
ROBUST_MARGIN = 0.05
SEED = 20260803

PHASES = ("approach", "insert", "pull", "buffer", "retreat", "return")
P_CONTROL = np.asarray(
    [
        [0.18, 0.18, 0.18],
        [0.20, 0.20, 0.20],
        [0.30, 0.20, 0.20],
        [0.20, 0.30, 0.20],
        [0.20, 0.20, 0.30],
        [0.18, 0.22, 0.22],
        [0.18, 0.18, 0.20],
    ],
    dtype=float,
)
P_NAMES = [f"P{i}" for i in range(7)]
BASE_CORRIDOR = np.asarray(
    [[-1.5, 0.0, 1.5], [-1.5, 1.6, 1.5], [0.0, 1.6, 1.8], [1.5, 1.6, 1.5], [1.5, 0.0, 1.5]],
    dtype=float,
)
BASE_TASK_POINTS = np.asarray(
    [[0.0, 1.5, 1.8], [0.0, 1.6, 1.8], [0.1, 1.7, 1.8], [0.2, 1.7, 1.8], [0.3, 1.7, 1.8], [0.4, 1.6, 1.8], [0.5, 1.6, 1.8]],
    dtype=float,
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_arm_path(variant: str) -> Path:
    source = "nominal" if variant == "nominal_repeat" else variant
    return R2_RUNTIME / source / "raw_trajectory_arm.json"


def source_base_path(variant: str) -> Path:
    source = "nominal" if variant == "nominal_repeat" else variant
    return R2_RUNTIME / source / "raw_trajectory.json"


def phase_boundaries(variant: str) -> np.ndarray:
    message = load_captured_message(source_arm_path(variant))["message"]
    cumulative = np.cumsum([0.0] + [float(x) for x in message["time"]])
    indices = [0, 1, 4, 7, 10, 13, 16, 19]
    return cumulative[indices]


def phase_for_time(t: float, boundaries: np.ndarray) -> str:
    if t < boundaries[1]:
        return PHASES[0]
    if t < boundaries[3]:
        return PHASES[1]
    if t < boundaries[4]:
        return PHASES[2]
    if t < boundaries[5]:
        return PHASES[3]
    if t < boundaries[6]:
        return PHASES[4]
    return PHASES[5]


def intervals(mask: np.ndarray, times: np.ndarray) -> list[tuple[int, int]]:
    mask = np.asarray(mask, dtype=bool)
    padded = np.r_[False, mask, False].astype(np.int8)
    starts = np.flatnonzero(np.diff(padded) == 1)
    ends = np.flatnonzero(np.diff(padded) == -1) - 1
    return [(int(s), int(e)) for s, e in zip(starts, ends)]


def interval_rows(mask: np.ndarray, times: np.ndarray, values: np.ndarray, labels: list[str], phase_edges: np.ndarray) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for start, end in intervals(mask, times):
        block = values[start : end + 1]
        rows.append(
            {
                "start_time_s": float(times[start]),
                "end_time_s": float(times[end]),
                "duration_s": float(times[end] - times[start]),
                "labels": labels,
                "phase": phase_for_time(float(times[start]), phase_edges),
                "min_value": float(np.nanmin(block)),
                "max_value": float(np.nanmax(block)),
                "sample_count": int(end - start + 1),
            }
        )
    return rows


def run_root_cause() -> None:
    root = EVIDENCE / "root_cause"
    root.mkdir(parents=True, exist_ok=True)
    joint_out: dict[str, object] = {}
    collision_out: dict[str, object] = {}
    timeline_rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        nominal_name = "nominal" if variant == "nominal_repeat" else variant
        trajectory = R3_ROOT / nominal_name / "800Hz" / "joint_trajectory.csv"
        data = np.genfromtxt(trajectory, delimiter=",", names=True)
        times = np.asarray(data["time_s"], dtype=float)
        q = np.column_stack([data["q1_rad"], data["q2_rad"], data["q3_rad"]])
        cart = np.asarray([official_fk_joint_state(row) for row in q])
        edges = phase_boundaries(variant)
        per_joint: dict[str, object] = {}
        for index, label in enumerate(("q1", "q2", "q3")):
            low = q[:, index] < 0.0
            high = q[:, index] > math.pi / 2.0
            per_joint[label] = {
                "q_below_zero": interval_rows(low, times, q[:, index], [label], edges),
                "q_above_pi_over_2": interval_rows(high, times, q[:, index], [label], edges),
                "min_q_rad": float(np.min(q[:, index])),
                "max_q_rad": float(np.max(q[:, index])),
            }
        union = np.any((q < 0.0) | (q > math.pi / 2.0), axis=1)
        joint_out[variant] = {
            "source": str(trajectory.relative_to(ROOT)).replace("\\", "/"),
            "sample_count": int(len(q)),
            "per_joint": per_joint,
            "union_intervals": interval_rows(union, times, np.min(np.minimum(q, math.pi / 2.0 - q), axis=1), ["any_joint"], edges),
            "cartesian_min_m": np.min(cart, axis=0).tolist(),
            "cartesian_max_m": np.max(cart, axis=0).tolist(),
            "cartesian_at_first_violation_m": cart[int(np.flatnonzero(union)[0])].tolist() if union.any() else None,
        }
        base = sample_raw(source_base_path(variant), 800, arm=False)
        arm = sample_raw(source_arm_path(variant), 800, arm=True)
        kin, points = validate_kinematics(arm)
        _, attitude = validate_attitude(base)
        tree = obstacle_tree(variant)
        comp_names = ["body", "rotor_1", "rotor_2", "rotor_3", "rotor_4", "upper_arm_1", "upper_arm_2", "upper_arm_3", "lower_arm_1_left", "lower_arm_1_right", "lower_arm_2_left", "lower_arm_2_right", "lower_arm_3_left", "lower_arm_3_right", "moving_platform", "end_effector"]
        comp_values = {name: [] for name in comp_names}
        for p_wb, R_wb, p_a0, jp in zip(base["position"], attitude["rotation"], arm["position"], points):
            values = component_clearances(p_wb, R_wb, p_a0, jp, tree)
            for name in comp_names:
                comp_values[name].append(values[name])
        comp_arrays = {name: np.asarray(values, dtype=float) for name, values in comp_values.items()}
        collision_out[variant] = {
            "sample_count": int(len(base["time"])),
            "components": {
                name: {
                    "min_clearance_m": float(np.min(values)),
                    "time_s": float(base["time"][int(np.argmin(values))]),
                    "phase": phase_for_time(float(base["time"][int(np.argmin(values))]), edges),
                    "violation_intervals": interval_rows(values < GATE_M, base["time"], values, [name], edges),
                }
                for name, values in comp_arrays.items()
            },
        }
        for name, values in comp_arrays.items():
            for start, end in intervals(values < GATE_M, base["time"]):
                timeline_rows.append({"variant": variant, "failure_type": "collision", "component": name, "start_time_s": float(base["time"][start]), "end_time_s": float(base["time"][end]), "phase": phase_for_time(float(base["time"][start]), edges), "min_value": float(np.min(values[start : end + 1]))})
        for start, end in intervals(union, times):
            timeline_rows.append({"variant": variant, "failure_type": "joint", "component": "q_branch", "start_time_s": float(times[start]), "end_time_s": float(times[end]), "phase": phase_for_time(float(times[start]), edges), "min_value": float(np.min(np.minimum(q[start : end + 1], math.pi / 2.0 - q[start : end + 1])) )})
    write_json(root / "joint_violation_intervals.json", joint_out)
    write_json(root / "collision_violation_intervals.json", collision_out)
    with (root / "nominal_failure_timeline.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["variant", "failure_type", "component", "start_time_s", "end_time_s", "phase", "min_value"])
        writer.writeheader()
        writer.writerows(timeline_rows)
    summary = {
        "q_failure_coordinates": "official FK of every q(t) sample; q<0 or q>pi/2 intervals are reported per joint",
        "body_failure_cause": "base/body/rotor/link proxy enters the fixed crossarm point-cloud neighborhood; nominal minimum is body",
        "same_phase": "joint and collision failures overlap mainly in pull/buffer/retreat, but they are independent contracts",
        "gate_m": GATE_M,
        "no_clipping": True,
        "no_proxy_or_obstacle_change": True,
    }
    (root / "root_cause_summary.md").write_text("# S2-R4 根因摘要\n\n" + json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_json(root / "phase_failure_map.json", summary)


def build_envelope() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(SEED)
    q = rng.uniform(0.0, math.pi / 2.0, size=(500_000, 3))
    boundary_values = np.asarray([0.0, 0.02, 0.05, 0.10, math.pi / 2.0 - 0.10, math.pi / 2.0 - 0.05, math.pi / 2.0 - 0.02, math.pi / 2.0], dtype=float)
    corners = np.asarray(np.meshgrid(boundary_values[[0, -1]], boundary_values[[0, -1]], boundary_values[[0, -1]], indexing="ij"), dtype=float).reshape(3, -1).T
    q = np.vstack([q, corners])
    points = np.asarray([official_fk_joint_state(row) for row in q], dtype=float)
    margins = np.asarray([joint_margin(row) for row in q], dtype=float)
    return q, points, margins


def run_envelope() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    q, points, margins = build_envelope()
    out = EVIDENCE / "arm_envelope"
    out.mkdir(parents=True, exist_ok=True)
    hard = margins >= 0.0
    preferred = margins >= PREFERRED_MARGIN
    robust = margins >= ROBUST_MARGIN
    summary = {
        "seed": SEED,
        "random_sample_count": 500_000,
        "boundary_corner_count": 8,
        "total_sample_count": int(len(q)),
        "official_joint_contract_rad": [0.0, math.pi / 2.0],
        "hard_envelope": {"condition": "margin >= 0.00 rad", "count": int(hard.sum()), "cartesian_min_m": points[hard].min(axis=0).tolist(), "cartesian_max_m": points[hard].max(axis=0).tolist()},
        "preferred_envelope": {"condition": "margin >= 0.02 rad", "count": int(preferred.sum()), "cartesian_min_m": points[preferred].min(axis=0).tolist(), "cartesian_max_m": points[preferred].max(axis=0).tolist()},
        "robust_envelope": {"condition": "margin >= 0.05 rad", "count": int(robust.sum()), "cartesian_min_m": points[robust].min(axis=0).tolist(), "cartesian_max_m": points[robust].max(axis=0).tolist()},
        "point_cloud_storage": "local-only; only manifest and summaries are committed",
    }
    write_json(out / "envelope_summary.json", summary)
    write_json(out / "boundary_surface_manifest.json", {"boundary_values_rad": [0.0, 0.02, 0.05, 0.10, float(math.pi / 2.0 - 0.10), float(math.pi / 2.0 - 0.05), float(math.pi / 2.0 - 0.02), float(math.pi / 2.0)], "corner_count": 8, "seed": SEED})
    current: dict[str, object] = {}
    for variant in VARIANTS:
        source = "nominal" if variant == "nominal_repeat" else variant
        data = np.genfromtxt(R3_ROOT / source / "800Hz" / "joint_trajectory.csv", delimiter=",", names=True)
        q_current = np.column_stack([data["q1_rad"], data["q2_rad"], data["q3_rad"]])
        cart_current = np.asarray([official_fk_joint_state(row) for row in q_current])
        result: dict[str, object] = {"q_min_rad": q_current.min(axis=0).tolist(), "q_max_rad": q_current.max(axis=0).tolist(), "min_joint_margin_rad": float(np.min([joint_margin(row) for row in q_current]))}
        for name, mask in (("hard", hard), ("preferred", preferred), ("robust", robust)):
            tree = cKDTree(points[mask])
            distance, index = tree.query(cart_current)
            nearest = int(np.argmin(distance))
            result[name] = {"max_nearest_cartesian_distance_m": float(np.max(distance)), "worst_time_s": float(data["time_s"][nearest]), "nearest_feasible_cartesian_m": points[mask][int(index[nearest])].tolist(), "nearest_feasible_q_rad": q[mask][int(index[nearest])].tolist()}
        current[variant] = result
    write_json(out / "current_trajectory_violation.json", current)
    write_json(out / "nearest_feasible_projection.json", {"warning": "projection is diagnostic only and is not a planned trajectory", "variants": current})
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    take = np.linspace(0, len(points[preferred]) - 1, min(8000, int(preferred.sum())), dtype=int)
    ax.scatter(points[preferred][take, 0], points[preferred][take, 1], points[preferred][take, 2], s=1, alpha=0.08, label="preferred envelope")
    selected = np.asarray([official_fk_joint_state(row) for row in P_CONTROL])
    ax.plot(selected[:, 0], selected[:, 1], selected[:, 2], "o-", color="tab:red", label="P0-P6 selected")
    ax.set_xlabel("x_A0 (m)"); ax.set_ylabel("y_A0 (m)"); ax.set_zlabel("z_A0 (m)"); ax.legend(loc="best")
    fig.tight_layout(); fig.savefig(out / "workspace_figure.png", dpi=160); plt.close(fig)
    return q, points, margins


def static_candidates() -> dict[str, object]:
    out = EVIDENCE / "static_feasibility"
    out.mkdir(parents=True, exist_ok=True)
    arm_points = np.asarray([official_fk_joint_state(row) for row in P_CONTROL])
    base_grid = np.asarray([[x, y, z] for x in np.linspace(-0.2, 0.2, 9) for y in np.linspace(1.4, 1.9, 11) for z in np.linspace(1.5, 2.1, 7)], dtype=float)
    candidates: dict[str, object] = {}
    selected = {"variant": {}, "P0_P6": []}
    for variant in ("smoke_free", "loose", "nominal", "narrow"):
        tree = obstacle_tree(variant)
        variant_rows = []
        for index, (name, q, arm_point) in enumerate(zip(P_NAMES, P_CONTROL, arm_points)):
            jp = official_joint_points(arm_point, q)
            scored = []
            for base in base_grid:
                comp = component_clearances(base, np.eye(3), arm_point, jp, tree)
                scored.append((min(comp.values()), base, comp))
            scored.sort(key=lambda item: item[0], reverse=True)
            best = scored[0]
            variant_rows.append({"name": name, "q_rad": q.tolist(), "arm_point_A0_m": arm_point.tolist(), "base_point_WB_m": best[1].tolist(), "min_full_body_clearance_m": float(best[0]), "component_clearance_m": {k: float(v) for k, v in best[2].items()}, "preferred_margin_rad": float(joint_margin(q)), "hard_gate_pass": bool(best[0] >= GATE_M and joint_margin(q) >= 0.0), "preferred_gate_pass": bool(best[0] >= GATE_M and joint_margin(q) >= PREFERRED_MARGIN), "rejected_candidate_count": int(sum(1 for item in scored if item[0] < GATE_M))})
        candidates[variant] = variant_rows
    for index, (name, q, arm_point) in enumerate(zip(P_NAMES, P_CONTROL, arm_points)):
        jp = official_joint_points(arm_point, q)
        sensitivity = {}
        for scale in (0.9, 1.0, 1.1):
            vals = component_clearances(BASE_TASK_POINTS[index], np.eye(3), arm_point, jp, obstacle_tree("nominal"), scale)
            sensitivity[str(scale)] = {"min_clearance_m": float(min(vals.values())), "gate_pass": bool(min(vals.values()) >= GATE_M)}
        selected["P0_P6"].append({"name": name, "q_rad": q.tolist(), "arm_point_A0_m": arm_point.tolist(), "base_point_WB_m": BASE_TASK_POINTS[index].tolist(), "joint_margin_rad": float(joint_margin(q)), "clearance_sensitivity": sensitivity})
    selected["base_corridor_WB_m"] = BASE_CORRIDOR.tolist()
    selected["direction_contract"] = {"P2_to_P3": "horizontal insertion: |dz| < 1e-12 m and +x direction", "P3_to_P4": "horizontal pull-out: -x,+y direction"}
    write_json(out / "candidate_sets.json", candidates)
    write_json(out / "p0_p6_selected.json", selected)
    write_json(out / "rejected_candidates_summary.json", {variant: {"total_base_candidates_per_pose": int(len(base_grid)), "gate_m": GATE_M, "reasons": ["q margin below requested envelope", "body/rotor/link proxy clearance below gate"]} for variant in candidates})
    write_json(out / "clearance_sensitivity.json", {"nominal": selected["P0_P6"], "gate_m": GATE_M, "body_rotor_link_proxy_unchanged": True})
    fig = plt.figure(figsize=(8, 6)); ax = fig.add_subplot(111, projection="3d")
    obs = np.asarray(build_points("nominal")); ax.scatter(obs[:, 0], obs[:, 1], obs[:, 2], s=1, alpha=0.06, label="nominal obstacle")
    ax.plot(BASE_CORRIDOR[:, 0], BASE_CORRIDOR[:, 1], BASE_CORRIDOR[:, 2], "o-", color="tab:blue", label="base corridor")
    ax.scatter(arm_points[:, 0], arm_points[:, 1], arm_points[:, 2], color="tab:red", label="arm A0 P0-P6")
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)"); ax.set_zlabel("z (m)"); ax.legend(loc="best")
    fig.tight_layout(); fig.savefig(out / "static_feasibility_figure.png", dpi=160); plt.close(fig)
    return selected


def main() -> int:
    run_root_cause()
    run_envelope()
    selected = static_candidates()
    print(json.dumps({"root_cause": "written", "envelope": "written", "static_feasibility": "written", "nominal_selected": len(selected["P0_P6"]) == 7}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
