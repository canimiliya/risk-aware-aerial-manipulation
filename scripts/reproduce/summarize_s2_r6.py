"""Build compact, machine-readable S2-R6 acceptance summaries from raw runs."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from planner_bridge.execution.playback_validator import sample_raw


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "docs/evidence/S2-R6/runtime"
OUT = ROOT / "docs/evidence/S2-R6/final_validation"
WEIGHTS = {
    "w0": "nominal_w0",
    "10w0": "nominal_10w0",
    "100w0": "nominal_100w0",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def envelope_metrics(run: Path, envelope: dict, tau: float) -> dict:
    arm = sample_raw(run / "trajectory_arm.json", 2000, arm=True)
    position = np.asarray(arm["position"], dtype=float)
    centers = np.asarray(envelope["centers_m"], dtype=float)
    radii = np.asarray(envelope["radii_m"], dtype=float)
    logits = (radii[None, :] ** 2 - np.sum((position[:, None, :] - centers[None, :, :]) ** 2, axis=2)) / tau
    max_logit = np.max(logits, axis=1)
    g = tau * (max_logit + np.log(np.mean(np.exp(logits - max_logit[:, None]), axis=1)))
    violation = np.maximum(0.0, -g)
    return {
        "min_g_m2": float(np.min(g)),
        "active_samples": int(np.count_nonzero(g < 0.0)),
        "max_violation_m2": float(np.max(violation)),
        "integral_v3_s": float(np.trapezoid(violation**3, arm["time"])),
    }


def path_length(run: Path) -> float:
    arm = sample_raw(run / "trajectory_arm.json", 2000, arm=True)
    return float(np.linalg.norm(np.diff(np.asarray(arm["position"], dtype=float), axis=0), axis=1).sum())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    envelope = read_json(ROOT / "docs/evidence/S2-R6/envelope/anchor_balls.json")
    calibration = read_json(ROOT / "docs/evidence/S2-R6/calibration.json")
    tau = float(calibration["tau0"])

    candidates = {}
    for label, name in WEIGHTS.items():
        validation = read_json(RUNTIME / name / "validation_multirate.json")
        candidates[label] = {
            "run": name,
            "weight": calibration["weight_candidates"][label],
            "nominal_hard_gate_pass": validation["nominal_hard_gate_pass"],
            "capture_exit": validation["capture_exit"],
            "q_min_rad_2000": validation["rates"]["2000"]["q_min_rad"],
            "q_max_rad_2000": validation["rates"]["2000"]["q_max_rad"],
            "clearance_m_2000": validation["rates"]["2000"]["min_full_body_clearance_m"],
            "dangerous_component": validation["rates"]["2000"]["dangerous_component"],
            "dangerous_time_s": validation["rates"]["2000"]["dangerous_time_s"],
            "direction_pass": validation["direction"]["pass"],
            "final_cost": validation["diagnostics"]["final_cost"],
            "planning_time_ms": validation["diagnostics"]["planning_time_ms"],
            "arm_jerk_cost": validation["arm_jerk_cost"],
            "diagnostics": {k: validation["diagnostics"][k] for k in ("record_count", "min_g", "max_active_samples", "max_violation", "max_barrier_cost", "integration_samples")},
            "final_output_envelope": envelope_metrics(RUNTIME / name, envelope, tau),
            "path_length_m": path_length(RUNTIME / name),
        }
    (OUT / "candidate_summary.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    final_name = "nominal_100w0"
    formal = {}
    for label in ("smoke_final_100w0", "loose_final_100w0", "nominal_repeat_final_100w0", "narrow_final_100w0"):
        v = read_json(RUNTIME / label / "validation_multirate.json")
        formal[label] = {
            "capture_exit": v["capture_exit"],
            "nominal_hard_gate_pass": v["nominal_hard_gate_pass"],
            "q_min_rad_2000": v["rates"]["2000"]["q_min_rad"],
            "q_max_rad_2000": v["rates"]["2000"]["q_max_rad"],
            "clearance_m_2000": v["rates"]["2000"]["min_full_body_clearance_m"],
            "dangerous_component": v["rates"]["2000"]["dangerous_component"],
            "dangerous_time_s": v["rates"]["2000"]["dangerous_time_s"],
            "direction_pass": v["direction"]["pass"],
            "final_cost": v["diagnostics"]["final_cost"],
            "planning_time_ms": v["diagnostics"]["planning_time_ms"],
            "arm_jerk_cost": v["arm_jerk_cost"],
        }
    final = read_json(RUNTIME / final_name / "validation_multirate.json")
    repeat = read_json(RUNTIME / "nominal_repeat_final_100w0" / "validation_multirate.json")
    final_arm = sample_raw(RUNTIME / final_name / "trajectory_arm.json", 2000, arm=True)
    repeat_arm = sample_raw(RUNTIME / "nominal_repeat_final_100w0" / "trajectory_arm.json", 2000, arm=True)
    delta = np.asarray(final_arm["position"]) - np.asarray(repeat_arm["position"])
    repeatability = {
        "reference": final_name,
        "repeat": "nominal_repeat_final_100w0",
        "sample_count_reference": int(len(final_arm["time"])),
        "sample_count_repeat": int(len(repeat_arm["time"])),
        "max_abs_arm_position_delta_m": float(np.max(np.abs(delta))),
        "rms_arm_position_delta_m": float(np.sqrt(np.mean(delta**2))),
        "q_min_delta_rad": (np.asarray(final["rates"]["2000"]["q_min_rad"]) - np.asarray(repeat["rates"]["2000"]["q_min_rad"])).tolist(),
        "clearance_delta_m": float(final["rates"]["2000"]["min_full_body_clearance_m"] - repeat["rates"]["2000"]["min_full_body_clearance_m"]),
        "gate_both_pass": bool(final["nominal_hard_gate_pass"] and repeat["nominal_hard_gate_pass"]),
    }
    (OUT / "repeatability.json").write_text(json.dumps(repeatability, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    disabled = read_json(RUNTIME / "round1_disabled" / "validation_multirate.json")
    ablation = {
        "A0_disabled": {
            "run": "round1_disabled",
            "q_min_rad_2000": disabled["rates"]["2000"]["q_min_rad"],
            "clearance_m_2000": disabled["rates"]["2000"]["min_full_body_clearance_m"],
            "direction_pass": disabled["direction"]["pass"],
            "final_cost": disabled["diagnostics"]["final_cost"],
            "planning_time_ms": disabled["diagnostics"]["planning_time_ms"],
            "arm_jerk_cost": disabled["arm_jerk_cost"],
        },
        "A1_enabled": {
            "run": final_name,
            "q_min_rad_2000": final["rates"]["2000"]["q_min_rad"],
            "clearance_m_2000": final["rates"]["2000"]["min_full_body_clearance_m"],
            "direction_pass": final["direction"]["pass"],
            "final_cost": final["diagnostics"]["final_cost"],
            "planning_time_ms": final["diagnostics"]["planning_time_ms"],
            "arm_jerk_cost": final["arm_jerk_cost"],
            "final_output_envelope": envelope_metrics(RUNTIME / final_name, envelope, tau),
            "path_length_m": path_length(RUNTIME / final_name),
        },
    }
    (OUT / "ablation.json").write_text(json.dumps(ablation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    frequency = {hz: final["rates"][str(hz)] for hz in (100, 200, 400, 800, 2000)}
    (OUT / "frequency_convergence.json").write_text(json.dumps(frequency, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "formal_runs.json").write_text(json.dumps(formal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidates": list(candidates), "formal_runs": list(formal), "repeat_max_delta_m": repeatability["max_abs_arm_position_delta_m"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
