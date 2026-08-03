from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .official_delta_kinematics import DeltaGeometry, joint_margin, official_fk_joint_state, official_ik, official_joint_points
from .official_flatness_wrapper import OfficialFlatnessMap, quaternion_to_rotation_wxyz


def _message(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["message"]


def _poly_eval(coef: list[float], order: int, u: float, derivative: int) -> float:
    values = np.asarray(coef[: order + 1], dtype=float)
    degree = order
    for _ in range(derivative):
        values = np.asarray([(degree - i) * values[i] for i in range(len(values) - 1)], dtype=float)
        degree -= 1
    if derivative > order:
        return 0.0
    powers = np.asarray([u ** (degree - i) for i in range(len(values))], dtype=float)
    return float(values @ powers)


def evaluate_message(message: dict, times: np.ndarray, arm: bool = False) -> dict[str, np.ndarray]:
    orders = message["order"]
    durations = np.asarray(message["time"], dtype=float)
    mag = float(message.get("mag_coeff", 1.0))
    total = float(np.sum(durations))
    rows = {name: [] for name in ("position", "velocity", "acceleration", "jerk")}
    for time in np.asarray(times, dtype=float):
        t = min(max(float(time), 0.0), total - np.finfo(float).eps)
        idx = 0
        while idx < len(durations) - 1 and t > durations[idx]:
            t -= durations[idx]
            idx += 1
        u = t / durations[idx]
        shift = int(sum(order + 1 for order in orders[:idx]))
        vectors = []
        for derivative in range(4):
            vals = []
            for axis in ("coef_x", "coef_y", "coef_z"):
                vals.append(_poly_eval(message[axis][shift:], orders[idx], u, derivative) / durations[idx] ** derivative)
            vectors.append(np.asarray(vals, dtype=float))
        if arm:
            vectors[0][2] = min(max(vectors[0][2], -0.23), -0.06)
        for name, value in zip(rows, vectors):
            rows[name].append(value)
    return {name: np.asarray(values, dtype=float) for name, values in rows.items()}


def sample_raw(path: Path, hz: int, arm: bool = False) -> dict[str, np.ndarray]:
    message = _message(path)
    times = np.arange(0.0, float(np.sum(message["time"])) + 0.5 / hz, 1.0 / hz)
    times = times[times <= float(np.sum(message["time"])) + 1e-10]
    data = evaluate_message(message, times, arm=arm)
    data["time"] = times
    data["yaw"] = np.zeros(len(times), dtype=float)
    data["yaw_dot"] = np.full(len(times), 0.01, dtype=float)
    return data


def validate_kinematics(arm_data: dict[str, np.ndarray]) -> tuple[dict, list[dict[str, np.ndarray]]]:
    q_values, residuals, margins, points = [], [], [], []
    for point in arm_data["position"]:
        q = official_ik(point)
        fk = official_fk_joint_state(q)
        q_values.append(q)
        residuals.append(float(np.linalg.norm(fk - point)) if np.isfinite(fk).all() else float("nan"))
        margins.append(joint_margin(q) if np.isfinite(q).all() else float("nan"))
        points.append(official_joint_points(point, q) if np.isfinite(q).all() else {})
    q_values = np.asarray(q_values)
    residuals = np.asarray(residuals)
    margins = np.asarray(margins)
    if len(q_values) > 1:
        qdot = np.gradient(q_values, arm_data["time"], axis=0, edge_order=2)
        qddot = np.gradient(qdot, arm_data["time"], axis=0, edge_order=2)
    else:
        qdot = qddot = np.zeros_like(q_values)
    result = {
        "samples": int(len(q_values)),
        "ik_no_solution_count": int(np.sum(~np.isfinite(q_values).all(axis=1))),
        "fk_residual_max_m": float(np.nanmax(residuals)) if np.isfinite(residuals).any() else float("nan"),
        "fk_residual_p99_m": float(np.nanpercentile(residuals, 99)) if np.isfinite(residuals).any() else float("nan"),
        "q_min_rad": np.nanmin(q_values, axis=0).tolist(),
        "q_max_rad": np.nanmax(q_values, axis=0).tolist(),
        "min_joint_margin_rad": float(np.nanmin(margins)),
        "qdot_max_rad_s": float(np.nanmax(np.abs(qdot))),
        "qddot_max_rad_s2": float(np.nanmax(np.abs(qddot))),
        "finite": bool(np.isfinite(q_values).all() and np.isfinite(qdot).all() and np.isfinite(qddot).all()),
        "joint_limits_pass": bool(np.isfinite(margins).all() and np.nanmin(margins) >= 0.0),
    }
    return {**result, "q": q_values, "qdot": qdot, "qddot": qddot}, points


def validate_attitude(base_data: dict[str, np.ndarray]) -> tuple[dict, dict[str, np.ndarray]]:
    flatness = OfficialFlatnessMap()
    thrust, quats, omegas, rotations = [], [], [], []
    for vel, acc, jerk, yaw, yaw_dot in zip(base_data["velocity"], base_data["acceleration"], base_data["jerk"], base_data["yaw"], base_data["yaw_dot"]):
        thr, quat, omg = flatness.forward(vel, acc, jerk, float(yaw), float(yaw_dot))
        thrust.append(thr)
        quats.append(quat)
        omegas.append(omg)
        rotations.append(quaternion_to_rotation_wxyz(quat))
    quats = np.asarray(quats)
    rotations = np.asarray(rotations)
    norms = np.linalg.norm(quats, axis=1)
    orth_errors = np.linalg.norm(np.einsum("nij,nkj->nik", rotations, rotations) - np.eye(3), axis=(1, 2))
    dets = np.linalg.det(rotations)
    result = {
        "samples": int(len(quats)),
        "quaternion_finite": bool(np.isfinite(quats).all()),
        "quaternion_norm_error_max": float(np.max(np.abs(norms - 1.0))),
        "rotation_orthogonality_error_max": float(np.max(orth_errors)),
        "det_min": float(np.min(dets)),
        "det_max": float(np.max(dets)),
        "thrust_min_N": float(np.min(thrust)),
        "thrust_max_N": float(np.max(thrust)),
        "omega_max_rad_s": float(np.max(np.abs(omegas))),
        "finite": bool(np.isfinite(quats).all() and np.isfinite(rotations).all() and np.isfinite(thrust).all() and np.isfinite(omegas).all()),
        "rotation_pass": bool(np.max(orth_errors) < 1e-8 and np.min(dets) > 0.999999),
        "thrust_pass": bool(np.min(thrust) > 0.0),
    }
    return result, {"quaternion": quats, "rotation": rotations, "thrust": np.asarray(thrust), "omega": np.asarray(omegas)}
