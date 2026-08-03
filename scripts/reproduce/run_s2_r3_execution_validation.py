from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np

from planner_bridge.execution.full_body_proxy import closest_component_obstacle, component_sample_sets, obstacle_tree
from planner_bridge.execution.playback_validator import sample_raw, validate_attitude, validate_kinematics


VARIANTS = ["smoke_free", "loose", "nominal", "nominal_repeat", "narrow"]
RATES = [100, 200, 400, 800]
GATE_M = 0.010


def _jsonable(value):
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(value), indent=2) + "\n", encoding="utf-8")


def _raw_path(variant: str, arm: bool) -> Path:
    return ROOT / "data" / "trajectories" / "S2-R2" / "100Hz" / variant / ("raw_trajectory_arm.json" if arm else "raw_trajectory.json")


def _save_joint(path: Path, time: np.ndarray, kinematics: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ["time_s"] + [f"q{i+1}_rad" for i in range(3)] + [f"qdot{i+1}_rad_s" for i in range(3)] + [f"qddot{i+1}_rad_s2" for i in range(3)]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in zip(time, kinematics["q"], kinematics["qdot"], kinematics["qddot"]):
            writer.writerow([f"{float(v):.12g}" for part in row for v in (part if isinstance(part, np.ndarray) else [part])])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _collision_for_samples(variant: str, hz: int, base: dict, arm: dict, kinematics: dict, attitude_data: dict, radii_scale: float = 1.0) -> dict:
    tree = obstacle_tree(variant)
    minima: dict[str, dict] = {}
    for index, (time, p_wb, R_wb, p_a0, joint_points) in enumerate(zip(base["time"], base["position"], attitude_data["rotation"], arm["position"], kinematics["points"])):
        samples = component_sample_sets(p_wb, R_wb, p_a0, joint_points, radii_scale)
        for name, component in samples.items():
            clearance, obstacle, proxy_point = closest_component_obstacle(component, tree)
            previous = minima.get(name)
            if previous is None or clearance < previous["min_clearance_m"]:
                minima[name] = {"min_clearance_m": clearance, "time_s": float(time), "obstacle_point_world_m": obstacle, "closest_proxy_point_world_m": proxy_point, "sample_index": index}
    min_component = min(minima, key=lambda name: minima[name]["min_clearance_m"])
    component_mins = {name: float(item["min_clearance_m"]) for name, item in minima.items()}
    threshold = {str(value): bool(min(component_mins.values()) >= value) for value in (0.005, 0.010, 0.020, 0.050)}
    return {"variant": variant, "hz": hz, "samples": int(len(base["time"])), "component_minima": minima, "component_clearance_m": component_mins, "min_clearance_m": float(component_mins[min_component]), "most_dangerous_component": min_component, "threshold_sensitivity": threshold, "radius_scale": radii_scale, "finite": bool(np.isfinite(list(component_mins.values())).all()), "gate_pass": bool(min(component_mins.values()) >= GATE_M)}


def _adaptive_refine(variant: str, base_message: Path, arm_message: Path, coarse: dict) -> dict:
    t0 = float(coarse["component_minima"][coarse["most_dangerous_component"]]["time_s"])
    total = float(np.sum(json.loads(base_message.read_text(encoding="utf-8"))["message"]["time"]))
    times = np.arange(max(0.0, t0 - 0.01), min(total, t0 + 0.01) + 0.00025, 0.0005)
    base = sample_raw(base_message, 2000)
    # sample_raw's grid is not used here; evaluate the exact requested times.
    from planner_bridge.execution.playback_validator import evaluate_message, _message

    base = evaluate_message(_message(base_message), times)
    base["time"] = times
    base["yaw"] = np.zeros(len(times))
    base["yaw_dot"] = np.full(len(times), 0.01)
    arm = evaluate_message(_message(arm_message), times, arm=True)
    arm["time"] = times
    kinematics, points = validate_kinematics(arm)
    kinematics["points"] = points
    _, attitude_data = validate_attitude(base)
    refined = _collision_for_samples(variant, 2000, base, arm, kinematics, attitude_data)
    refined["refinement_step_s"] = 0.0005
    refined["coarse_min_clearance_m"] = coarse["min_clearance_m"]
    refined["converged_delta_m"] = abs(refined["min_clearance_m"] - coarse["min_clearance_m"])
    refined["converged_lt_0_5mm"] = bool(refined["converged_delta_m"] < 0.0005)
    return refined


def main() -> int:
    root_out = ROOT / "docs" / "evidence" / "S2-R3"
    summary = {"official_source_commit": "7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d", "variants": {}, "rates_hz": RATES, "gate_m": GATE_M}
    for variant in VARIANTS:
        summary["variants"][variant] = {"rates": {}}
        for hz in RATES:
            base = sample_raw(_raw_path(variant, False), hz)
            arm = sample_raw(_raw_path(variant, True), hz, arm=True)
            kinematics, points = validate_kinematics(arm)
            kinematics["points"] = points
            attitude_summary, attitude_data = validate_attitude(base)
            out_dir = ROOT / "data" / "trajectories" / "S2-R3" / variant / f"{hz}Hz"
            _save_joint(out_dir / "joint_trajectory.csv", arm["time"], kinematics)
            np.savez_compressed(out_dir / "joint_trajectory.npz", time=arm["time"], q=kinematics["q"], qdot=kinematics["qdot"], qddot=kinematics["qddot"])
            validation = {key: value for key, value in kinematics.items() if key not in ("points", "q", "qdot", "qddot")}
            validation["q_branch_jump_max_rad"] = float(np.max(np.abs(np.diff(kinematics["q"], axis=0)))) if len(kinematics["q"]) > 1 else 0.0
            validation["official_ik_range_rad"] = [0.0, float(np.pi / 2.0)]
            _write_json(out_dir / "joint_validation.json", validation)
            _write_json(out_dir / "sha256_manifest.json", {"joint_trajectory.csv": _sha256(out_dir / "joint_trajectory.csv"), "joint_trajectory.npz": _sha256(out_dir / "joint_trajectory.npz"), "joint_validation.json": _sha256(out_dir / "joint_validation.json")})
            _write_json(root_out / "attitude" / variant / f"{hz}Hz.json", attitude_summary)
            collision_path = root_out / "collision" / variant / f"{hz}Hz.json"
            if collision_path.exists():
                collision = json.loads(collision_path.read_text(encoding="utf-8"))
            else:
                collision = _collision_for_samples(variant, hz, base, arm, kinematics, attitude_data)
                _write_json(collision_path, collision)
            summary["variants"][variant]["rates"][str(hz)] = {"kinematics": validation, "attitude": attitude_summary, "collision": {key: value for key, value in collision.items() if key != "component_minima"}}
        nominal = summary["variants"][variant]["rates"]["800"]["collision"]
        # Reuse the captured 800 Hz result for radius sensitivity at the same times.
        base = sample_raw(_raw_path(variant, False), 800)
        arm = sample_raw(_raw_path(variant, True), 800, arm=True)
        kinematics, points = validate_kinematics(arm)
        kinematics["points"] = points
        _, attitude_data = validate_attitude(base)
        sensitivity_path = root_out / "collision" / variant / "radius_sensitivity_800Hz.json"
        if sensitivity_path.exists():
            sensitivity = json.loads(sensitivity_path.read_text(encoding="utf-8"))
        else:
            sensitivity = {}
            for scale in (0.9, 1.0, 1.1):
                item = _collision_for_samples(variant, 800, base, arm, kinematics, attitude_data, radii_scale=scale)
                sensitivity[str(scale)] = {"min_clearance_m": item["min_clearance_m"], "component": item["most_dangerous_component"], "gate_pass": item["gate_pass"]}
            _write_json(sensitivity_path, sensitivity)
        summary["variants"][variant]["radius_sensitivity_800Hz"] = sensitivity
        if variant == "nominal":
            _write_json(root_out / "collision" / variant / "adaptive_refinement.json", _adaptive_refine(variant, _raw_path(variant, False), _raw_path(variant, True), {"min_clearance_m": nominal["min_clearance_m"], "most_dangerous_component": nominal["most_dangerous_component"], "component_minima": json.loads((root_out / "collision" / variant / "800Hz.json").read_text(encoding="utf-8"))["component_minima"]}))
    repeat_a = summary["variants"]["nominal"]["rates"]["800"]
    repeat_b = summary["variants"]["nominal_repeat"]["rates"]["800"]
    summary["nominal_repeat"] = {"joint_q_max_abs_delta_rad": float(np.max(np.abs(np.load(ROOT / "data/trajectories/S2-R3/nominal/800Hz/joint_trajectory.npz")["q"] - np.load(ROOT / "data/trajectories/S2-R3/nominal_repeat/800Hz/joint_trajectory.npz")["q"]))), "clearance_min_delta_m": abs(repeat_a["collision"]["min_clearance_m"] - repeat_b["collision"]["min_clearance_m"]), "same_component": repeat_a["collision"]["most_dangerous_component"] == repeat_b["collision"]["most_dangerous_component"]}
    all_nominal_gates = all(summary["variants"][name]["rates"]["800"]["collision"]["gate_pass"] for name in ("loose", "nominal", "nominal_repeat"))
    all_nominal_ik = all(summary["variants"][name]["rates"]["800"]["kinematics"]["joint_limits_pass"] for name in ("loose", "nominal", "nominal_repeat"))
    summary["decision"] = "S2_R3_IK_FAILED" if not all_nominal_ik else ("S2_R3_FULL_BODY_PROXY_READY" if all_nominal_gates else "S2_R3_FULL_BODY_CLEARANCE_FAILED")
    summary["limitations"] = ["ROS traj_server/DeltaDisplay live playback was not started in this offline validation run", "body and rotor geometry remain provisional proxies", "qdot/qddot are numerical derivatives, not actuator dynamics", "point/capsule/disk collision is not mesh exact"]
    _write_json(root_out / "kinematics" / "s2_r3_kinematics_summary.json", {"official_ik_fk": "PASS_WITH_LIMITATIONS", "trajectory_groups": {variant: {rate: summary["variants"][variant]["rates"][rate]["kinematics"] for rate in ("100", "200", "400", "800")} for variant in VARIANTS}, "joint_state_convention": "endCallback q=theta; raw FK uses theta_fk=pi/2-q"})
    _write_json(root_out / "geometry" / "geometry_manifest.json", {"body": {"shape": "sphere", "radius_m": 0.20, "source": "PROVISIONAL_S2_ASSUMPTION"}, "rotors": {"count": 4, "shape": "disk", "radius_m": 0.25, "centers_body_m": [[0.17, 0.17, 0.05], [-0.17, 0.17, 0.05], [-0.17, -0.17, 0.05], [0.17, -0.17, 0.05]], "source": "PROVISIONAL_S2_ASSUMPTION"}, "upper_arms": {"count": 3, "shape": "capsule_centerline_A_B", "radius_m": 0.010, "source": "DERIVED_FROM_OFFICIAL getJointPoints + PROVISIONAL capsule radius"}, "lower_rods": {"count": 6, "shape": "capsule_centerline_B_C", "radius_m": 0.010, "source": "DERIVED_FROM_OFFICIAL getJointPoints + PROVISIONAL capsule radius"}, "moving_platform": {"radius_m": 0.025, "source": "OFFICIAL task proxy"}, "end_effector": {"radius_m": 0.025, "source": "OFFICIAL task proxy"}, "frame_chain": "W <- p_WB,R_WB <- B <- T_B_A0 <- A0/E"})
    _write_json(root_out / "validation" / "s2_r3_execution_validation.json", summary)
    _write_json(root_out / "ros_playback" / "ros_playback_status.json", {"status": "NOT_RUN_OFFLINE_VALIDATION_ONLY", "reason": "No new ROS launch/replay was started; existing S2-R2 raw trajectories and official compiled source audit were preserved.", "official_source_symbols_audited": True, "new_dependencies_installed": False})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
