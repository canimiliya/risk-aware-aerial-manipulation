"""Build and numerically certify the S2-R6 Cartesian execution envelope."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import yaml

from planner_bridge.execution.official_delta_kinematics import official_fk_joint_state, official_ik
from planner_bridge.workspace.delta_arm_model import DeltaArmModel


ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "docs/evidence/S2-R6/envelope"
SEED = 20260804
RADIUS_M = 0.0015
SAMPLES_PER_BALL = 2000
LOWER = 0.0
UPPER = math.pi / 2.0


def stable_g(points: np.ndarray, centers: np.ndarray, radii: np.ndarray, tau: float) -> np.ndarray:
    z = radii[None, :] ** 2 - ((points[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    logits = z / tau
    max_logit = logits.max(axis=1)
    return tau * (max_logit + np.log(np.exp(logits - max_logit[:, None]).mean(axis=1)))


def load_round1_points() -> tuple[np.ndarray, np.ndarray]:
    data = yaml.safe_load((ROOT / "docs/evidence/S2-R5/rounds/round_1/tasks.yaml").read_text(encoding="utf-8"))
    rows = [row for row in data["nominal"]["inter_points"] if int(row[0]) == 3]
    points = np.asarray([row[4:7] for row in rows], dtype=float)
    qs = np.asarray([official_ik(point) for point in points], dtype=float)
    if not np.isfinite(qs).all() or np.any(qs < LOWER) or np.any(qs > UPPER):
        raise RuntimeError("Round1 fixed points do not lie on the official [0, pi/2] branch")
    return points, qs


def build_corridor(qs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    q_path = []
    for start, end in zip(qs[:-1], qs[1:]):
        for u in np.linspace(0.0, 1.0, 7, endpoint=False):
            q_path.append((1.0 - u) * start + u * end)
    q_path.append(qs[-1])
    q_path_array = np.asarray(q_path, dtype=float)
    centers = np.asarray([official_fk_joint_state(q) for q in q_path_array], dtype=float)
    return q_path_array, centers


def certify_ball(center: np.ndarray, rng: np.random.Generator) -> dict[str, object]:
    direction = rng.normal(size=(SAMPLES_PER_BALL, 3))
    direction /= np.linalg.norm(direction, axis=1)[:, None]
    interior_radius = RADIUS_M * rng.random(SAMPLES_PER_BALL) ** (1.0 / 3.0)
    interior = center + direction * interior_radius[:, None]
    boundary = center + direction * RADIUS_M
    checked = np.vstack([interior, boundary])
    qs = np.asarray([official_ik(point) for point in checked], dtype=float)
    hard_pass = bool(np.isfinite(qs).all() and np.all(qs >= LOWER - 1e-10) and np.all(qs <= UPPER + 1e-10))
    return {
        "center_m": center.tolist(),
        "radius_m": RADIUS_M,
        "interior_samples": SAMPLES_PER_BALL,
        "boundary_samples": SAMPLES_PER_BALL,
        "hard_branch_pass": hard_pass,
        "min_q_rad": np.nanmin(qs, axis=0).tolist(),
        "max_q_rad": np.nanmax(qs, axis=0).tolist(),
        "nonfinite_ik_count": int(np.count_nonzero(~np.isfinite(qs))),
    }


def main() -> None:
    EV.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    fixed_points, fixed_qs = load_round1_points()
    corridor_qs, centers = build_corridor(fixed_qs)
    radii = np.full(len(centers), RADIUS_M, dtype=float)
    tau = float(np.median(radii**2) / 10.0)

    model = DeltaArmModel()
    random_q = rng.uniform(LOWER, UPPER, size=(1_000_000, 3))
    random_fk, random_valid = model.fk_batch(UPPER - random_q)
    corners = np.asarray(np.meshgrid(*[(LOWER, UPPER)] * 3), dtype=float).T.reshape(-1, 3)
    corner_fk, corner_valid = model.fk_batch(UPPER - corners)
    boundary_values = np.asarray([LOWER, 0.05, 0.10, UPPER - 0.10, UPPER - 0.05, UPPER])
    boundary_q = []
    for axis in range(3):
        for value in boundary_values:
            other = rng.uniform(LOWER, UPPER, size=(2000, 2))
            rows = np.zeros((len(other), 3), dtype=float)
            rows[:, axis] = value
            rows[:, [i for i in range(3) if i != axis]] = other
            boundary_q.append(rows)
    boundary_q = np.vstack(boundary_q)
    boundary_fk, boundary_valid = model.fk_batch(UPPER - boundary_q)

    certifications = [certify_ball(center, rng) for center in centers]
    if not all(item["hard_branch_pass"] for item in certifications):
        raise RuntimeError("at least one anchor ball failed the hard-branch certification")
    center_q_margin = np.min(np.minimum(corridor_qs, UPPER - corridor_qs), axis=1)
    if np.any(center_q_margin < 0.05 - 1e-10):
        raise RuntimeError("anchor center left the robust q margin")

    center_distances = np.linalg.norm(np.diff(centers, axis=0), axis=1)
    g_on_corridor = stable_g(centers, centers, radii, tau)
    nearest_fixed = np.min(np.linalg.norm(fixed_points[:, None, :] - centers[None, :, :], axis=2), axis=1)
    coverage = {
        "round1_fixed_point_count": int(len(fixed_points)),
        "round1_fixed_point_nearest_center_max_m": float(nearest_fixed.max()),
        "round1_fixed_points_within_anchor_balls": bool(np.all(nearest_fixed <= RADIUS_M + 1e-12)),
        "interpolated_corridor_count": int(len(centers)),
        "interpolated_corridor_g_min": float(g_on_corridor.min()),
        "interpolated_corridor_g_nonnegative": bool(np.all(g_on_corridor >= 0.0)),
        "raw_round1_polynomial_is_not_claimed_covered": True,
    }
    connectivity = {
        "ordered_anchor_count": int(len(centers)),
        "adjacent_distance_max_m": float(center_distances.max()),
        "adjacent_distance_min_m": float(center_distances.min()),
        "minimum_ball_overlap_margin_m": float((2.0 * RADIUS_M - center_distances).min()),
        "all_adjacent_balls_overlap": bool(np.all(center_distances <= 2.0 * RADIUS_M)),
    }
    source_contract = """# S2-R6 execution-envelope source contract

- Official execution branch: `q_i in [0, pi/2]`.
- Geometry/FK/IK: project-owned translations of the official DeltaDisplay implementation.
- Round1 task/map/proxy/gate are frozen; fixed points are read from `docs/evidence/S2-R5/rounds/round_1/tasks.yaml`.
- The 64 ordered centers are generated by linear interpolation in the official joint branch and evaluated by official FK.
- Ball validation is numerical and conservative; it is not a formal proof.
- The raw Round1 violating polynomial is not relabeled as covered. The envelope covers the desired fixed-point/q-branch corridor used as the S2-R6 planner target.
"""
    (EV / "source_contract.md").write_text(source_contract, encoding="utf-8")
    (EV / "anchor_balls.json").write_text(json.dumps({
        "count": int(len(centers)),
        "radius_m": RADIUS_M,
        "centers_m": centers.tolist(),
        "radii_m": radii.tolist(),
        "center_q_rad": corridor_qs.tolist(),
        "center_joint_margin_min_rad": float(center_q_margin.min()),
        "tau0": tau,
        "fixed_seed": SEED,
    }, indent=2) + "\n", encoding="utf-8")
    (EV / "local_certification.json").write_text(json.dumps({
        "fixed_seed": SEED,
        "samples_per_ball": SAMPLES_PER_BALL,
        "total_ball_samples": int(len(centers) * SAMPLES_PER_BALL * 2),
        "hard_branch": {"lower_rad": LOWER, "upper_rad": UPPER},
        "preferred_definition": {"q1_q3_min_rad": 0.02, "q2_min_rad": 0.05, "upper_margin_rad": 0.02},
        "robust_definition": {"all_q_margin_min_rad": 0.05},
        "all_balls_hard_branch_pass": True,
        "certifications": certifications,
    }, indent=2) + "\n", encoding="utf-8")
    (EV / "corridor_connectivity.json").write_text(json.dumps(connectivity, indent=2) + "\n", encoding="utf-8")
    (EV / "round1_coverage.json").write_text(json.dumps(coverage, indent=2) + "\n", encoding="utf-8")
    sample_manifest = {
        "fixed_seed": SEED,
        "random_fk_sample_count": int(len(random_q)),
        "random_fk_valid_count": int(random_valid.sum()),
        "corner_count": int(len(corners)),
        "corner_fk_valid_count": int(corner_valid.sum()),
        "boundary_layer_sample_count": int(len(boundary_q)),
        "boundary_fk_valid_count": int(boundary_valid.sum()),
        "branch": "[0, pi/2]",
        "random_q_min_rad": random_q.min(axis=0).tolist(),
        "random_q_max_rad": random_q.max(axis=0).tolist(),
    }
    (EV / "envelope_manifest.json").write_text(json.dumps({
        "source_commit": "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d",
        "round1_baseline": True,
        "anchor_count": int(len(centers)),
        "radius_m": RADIUS_M,
        "tau0": tau,
        "workspace_sampling": sample_manifest,
        "local_certification": "local_certification.json",
        "numeric_conservative_only": True,
    }, indent=2) + "\n", encoding="utf-8")
    for path in sorted(EV.glob("*.json")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"{path.name}: {digest}")
    print(json.dumps({"anchor_count": len(centers), "tau0": tau, "coverage": coverage, "connectivity": connectivity, "workspace": sample_manifest}, indent=2))


if __name__ == "__main__":
    main()
