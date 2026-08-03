"""Validate S2-R4 real AM-Planner captures at the official execution layer."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np

from planner_bridge.execution.full_body_proxy import component_clearances, obstacle_tree
from planner_bridge.execution.official_delta_kinematics import joint_margin
from planner_bridge.execution.playback_validator import sample_raw, validate_attitude, validate_kinematics
from planner_bridge.export.sampling import load_captured_message, message_contract


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "docs/evidence/S2-R4/runtime"
EVIDENCE = ROOT / "docs/evidence/S2-R4"
RUNS = {
    "smoke_free": "smoke_free_run_02",
    "loose": "loose_run_01",
    "nominal": "nominal_run_01",
    "nominal_repeat": "nominal_repeat_run_01",
    "narrow": "narrow_run_01",
}
RATES = (100, 200, 400, 800)
GATE_M = 0.010
COMPONENTS = ("body", "rotor_1", "rotor_2", "rotor_3", "rotor_4", "upper_arm_1", "upper_arm_2", "upper_arm_3", "lower_arm_1_left", "lower_arm_1_right", "lower_arm_2_left", "lower_arm_2_right", "lower_arm_3_left", "lower_arm_3_right", "moving_platform", "end_effector")


def run_dir(variant: str) -> Path:
    return RUNTIME / RUNS[variant]


def finite_and_dynamic(data: dict[str, np.ndarray]) -> dict[str, object]:
    values = np.concatenate([data["position"].ravel(), data["velocity"].ravel(), data["acceleration"].ravel()])
    return {"finite": bool(np.isfinite(values).all()), "dynamic": bool(np.max(np.ptp(data["position"], axis=0)) > 1e-6), "duration_s": float(data["time"][-1]), "position_min_m": data["position"].min(axis=0).tolist(), "position_max_m": data["position"].max(axis=0).tolist(), "max_speed_m_s": float(np.linalg.norm(data["velocity"], axis=1).max()), "max_acceleration_m_s2": float(np.linalg.norm(data["acceleration"], axis=1).max())}


def validate_frequency(variant: str, hz: int) -> dict[str, object]:
    source = run_dir(variant)
    base = sample_raw(source / "trajectory.json", hz, arm=False)
    arm = sample_raw(source / "trajectory_arm.json", hz, arm=True)
    kin, points = validate_kinematics(arm)
    attitude, attitude_data = validate_attitude(base)
    tree = obstacle_tree(variant)
    component_values = {name: [] for name in COMPONENTS}
    for p_wb, R_wb, p_a0, jp in zip(base["position"], attitude_data["rotation"], arm["position"], points):
        values = component_clearances(p_wb, R_wb, p_a0, jp, tree)
        for name in COMPONENTS:
            component_values[name].append(values[name])
    minima = {name: {"min_clearance_m": float(np.min(values)), "time_s": float(base["time"][int(np.argmin(values))])} for name, values in {k: np.asarray(v) for k, v in component_values.items()}.items()}
    dangerous = min(minima, key=lambda name: minima[name]["min_clearance_m"])
    base_summary = finite_and_dynamic(base)
    arm_summary = finite_and_dynamic(arm)
    result = {
        "variant": variant,
        "hz": hz,
        "sample_count": int(len(base["time"])),
        "base": base_summary,
        "arm_cartesian": arm_summary,
        "kinematics": {k: v for k, v in kin.items() if k not in ("q", "qdot", "qddot")},
        "attitude": attitude,
        "component_minima": minima,
        "min_clearance_m": float(minima[dangerous]["min_clearance_m"]),
        "most_dangerous_component": dangerous,
        "full_body_gate_pass": bool(minima[dangerous]["min_clearance_m"] >= GATE_M),
        "finite": bool(base_summary["finite"] and arm_summary["finite"] and kin["finite"] and attitude["finite"]),
        "joint_gate_pass": bool(kin["joint_limits_pass"]),
    }
    out = EVIDENCE / "validation" / variant / f"{hz}Hz.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def source_contracts(variant: str) -> dict[str, object]:
    source = run_dir(variant)
    process_file = source / "processes.json"
    processes = json.loads(process_file.read_text(encoding="utf-8")) if process_file.exists() else {"capture_exit": None, "wrapper_complete": False}
    base = load_captured_message(source / "trajectory.json")
    arm = load_captured_message(source / "trajectory_arm.json")
    log = (source / "roslaunch.log").read_text(encoding="utf-8", errors="replace")
    return {
        "capture_exit": processes.get("capture_exit"),
        "wrapper_complete": bool(processes.get("wrapper_complete", process_file.exists())),
        "base_contract": message_contract(base),
        "arm_contract": message_contract(arm),
        "raw_files_present": True,
        "jps_success": "JPS path searching time" in log and "JPS search path!" in log,
        "minco_success": "MINCO setup successfully!" in log and "Finish optimization!" in log,
        "gpu_success": "successfully initialized on cuda" in log,
        "trajectory_published": "The trajectory is published!" in log,
        "nan_inf": int(base["statistics"].get("nan_count", 0)) + int(arm["statistics"].get("nan_count", 0)) + int(base["statistics"].get("inf_count", 0)) + int(arm["statistics"].get("inf_count", 0)),
    }


def direction_check() -> dict[str, object]:
    task = json.loads((EVIDENCE / "static_feasibility/p0_p6_selected.json").read_text(encoding="utf-8"))
    points = task["P0_P6"]
    p2 = np.asarray(points[2]["arm_point_A0_m"], dtype=float)
    p3 = np.asarray(points[3]["arm_point_A0_m"], dtype=float)
    p4 = np.asarray(points[4]["arm_point_A0_m"], dtype=float)
    v23, v34 = p3 - p2, p4 - p3
    return {"P2_to_P3": {"delta_A0_m": v23.tolist(), "horizontal": bool(abs(v23[2]) < 1e-12), "positive_x": bool(v23[0] > 0.0), "direction_error": float(abs(v23[2]))}, "P3_to_P4": {"delta_A0_m": v34.tolist(), "horizontal": bool(abs(v34[2]) < 1e-12), "negative_x_positive_y": bool(v34[0] < 0.0 and v34[1] > 0.0), "direction_error": float(abs(v34[2]))}, "pass": bool(abs(v23[2]) < 1e-12 and v23[0] > 0.0 and abs(v34[2]) < 1e-12 and v34[0] < 0.0 and v34[1] > 0.0)}


def main() -> int:
    summary: dict[str, object] = {"variants": {}, "rates_hz": list(RATES), "gate_m": GATE_M}
    for variant in RUNS:
        contracts = source_contracts(variant)
        rates = {str(hz): validate_frequency(variant, hz) for hz in RATES}
        adaptive = validate_frequency(variant, 2000) if variant in ("nominal", "nominal_repeat") else None
        summary["variants"][variant] = {"contracts": contracts, "rates": rates, "adaptive_2000Hz": adaptive}
    nominal = summary["variants"]["nominal"]["rates"]["800"]
    repeat = summary["variants"]["nominal_repeat"]["rates"]["800"]
    nominal_raw = validate_kinematics(sample_raw(run_dir("nominal") / "trajectory_arm.json", 800, arm=True))[0]["q"]
    repeat_raw = validate_kinematics(sample_raw(run_dir("nominal_repeat") / "trajectory_arm.json", 800, arm=True))[0]["q"]
    summary["direction"] = direction_check()
    summary["nominal_repeat"] = {"q_range_max_abs_delta_rad": float(np.max(np.abs(nominal_raw - repeat_raw))), "q_path_max_abs_delta_rad": float(np.max(np.abs(nominal_raw - repeat_raw))), "clearance_min_abs_delta_m": float(abs(nominal["min_clearance_m"] - repeat["min_clearance_m"])), "same_component": nominal["most_dangerous_component"] == repeat["most_dangerous_component"]}
    valid_variants = []
    for variant, data in summary["variants"].items():
        c = data["contracts"]
        n = data["rates"]["800"]
        valid_variants.append(bool(c["capture_exit"] == 0 and c["jps_success"] and c["minco_success"] and c["gpu_success"] and c["trajectory_published"] and c["nan_inf"] == 0 and n["base"]["dynamic"] and n["arm_cartesian"]["dynamic"]))
    required_variants = ("smoke_free", "loose", "nominal", "nominal_repeat")
    required_runtime_ok = all(valid_variants[list(RUNS).index(variant)] for variant in required_variants)
    nominal_ready = bool(required_runtime_ok and summary["variants"]["nominal"]["rates"]["800"]["joint_gate_pass"] and summary["variants"]["nominal"]["rates"]["800"]["full_body_gate_pass"] and summary["variants"]["nominal_repeat"]["rates"]["800"]["full_body_gate_pass"] and summary["direction"]["pass"] and summary["nominal_repeat"]["q_path_max_abs_delta_rad"] == 0.0)
    if not required_runtime_ok:
        decision = "S2_R4_PLANNER_RUNTIME_FAILED"
    elif not summary["variants"]["nominal"]["rates"]["800"]["joint_gate_pass"]:
        decision = "S2_R4_JOINT_LIMIT_FAILED"
    elif not summary["variants"]["nominal"]["rates"]["800"]["full_body_gate_pass"]:
        decision = "S2_R4_FULL_BODY_CLEARANCE_FAILED"
    elif not summary["direction"]["pass"]:
        decision = "S2_R4_DIRECTION_FAILED"
    elif nominal_ready:
        decision = "S2_R4_EXECUTION_FEASIBLE_READY"
    else:
        decision = "S2_R4_PLANNER_RUNTIME_FAILED"
    summary["decision"] = decision
    summary["ros_playback"] = {"status": "NOT_RUN_LIVE_DELTA_DISPLAY", "reason": "real se3_node capture succeeded; no new DeltaDisplay live playback was launched"}
    (EVIDENCE / "validation/s2_r4_execution_validation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "variants": list(RUNS), "nominal_ready": nominal_ready}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
