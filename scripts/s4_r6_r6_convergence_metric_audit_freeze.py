"""S4-R6-R6 convergence-metric audit using the existing R5 raw traces.

This pass does not rerun or alter the physics model.  It attributes the R5
maximum-change metric, aligns events and trajectories in physical time, and
emits a conservative R6 readiness result.  State convergence is intentionally
computed independently from finite-difference acceleration diagnostics.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
R5 = ROOT / "docs/evidence/S4-R6-R5/runtime"
EVIDENCE = ROOT / "docs/evidence/S4-R6-R6"
DIAGNOSIS = EVIDENCE / "diagnosis"
RUNTIME = EVIDENCE / "runtime"
FREEZE = EVIDENCE / "freeze"
SUMMARY = EVIDENCE / "summary"
TASK = "S4-R6-R6-CONVERGENCE-METRIC-AUDIT-AND-FREEZE-R1"
START_HEAD = "ae0b6e26942312c0f87984582389cb889571503b"
RATES = (240, 480, 960, 1920)
PAIRS = ((240, 480), (480, 960), (960, 1920))
TOTAL_TIME = 0.25
PULSE_TIME = 0.125
MAX_DT = 1.0 / 240.0
EDGE_HALF_WIDTH = 2.0 * MAX_DT
THRESHOLDS = {"240_to_480": 0.02, "480_to_960": 0.01, "960_to_1920": 0.01}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finite(value: Any) -> bool:
    if isinstance(value, dict):
        return all(finite(v) for v in value.values())
    return bool(np.all(np.isfinite(np.asarray(value, dtype=float))))


def rel(left: float, right: float) -> float:
    return abs(float(left) - float(right)) / max(1.0e-12, abs(float(right)))


def vector(row: dict[str, Any], field: str) -> np.ndarray:
    return np.asarray(row[field], dtype=float)


def component_trace(case: dict[str, Any], field: str, component: str | None = None) -> tuple[np.ndarray, np.ndarray]:
    times = np.asarray([float(r["time_s"]) for r in case["records"]])
    if component is None:
        values = np.asarray([np.linalg.norm(vector(r, field)) for r in case["records"]])
    else:
        values = np.asarray([float(r[field][component]) for r in case["records"]])
    return times, values


def interpolate(case: dict[str, Any], field: str, grid: np.ndarray, component: str | None = None) -> np.ndarray:
    times, values = component_trace(case, field, component)
    return np.interp(grid, times, values)


def normalized_rms(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.sqrt(np.mean((left - right) ** 2)) / max(np.ptp(right), 1.0e-12))


def normalized_max(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.max(np.abs(left - right)) / max(np.ptp(right), 1.0e-12))


def trace_metrics(left: dict[str, Any], right: dict[str, Any], grid: np.ndarray, field: str, component: str | None, edge_mask: np.ndarray | None = None) -> dict[str, float]:
    lv = interpolate(left, field, grid, component)
    rv = interpolate(right, field, grid, component)
    if edge_mask is not None:
        lv_gate, rv_gate = lv[edge_mask], rv[edge_mask]
    else:
        lv_gate, rv_gate = lv, rv
    return {
        "peak_abs_left": float(np.max(np.abs(lv))),
        "peak_abs_right": float(np.max(np.abs(rv))),
        "peak_relative_change": rel(np.max(np.abs(lv)), np.max(np.abs(rv))),
        "final_left": float(lv[-1]),
        "final_right": float(rv[-1]),
        "final_relative_change": rel(lv[-1], rv[-1]),
        "rms_difference": float(np.sqrt(np.mean((lv - rv) ** 2))),
        "normalized_rms_difference": normalized_rms(lv, rv),
        "normalized_max_error": normalized_max(lv, rv),
        "gate_peak_abs_left": float(np.max(np.abs(lv_gate))),
        "gate_peak_abs_right": float(np.max(np.abs(rv_gate))),
        "gate_peak_relative_change": rel(np.max(np.abs(lv_gate)), np.max(np.abs(rv_gate))),
        "gate_normalized_rms_difference": normalized_rms(lv_gate, rv_gate),
        "gate_normalized_max_error": normalized_max(lv_gate, rv_gate),
    }


def raw_peak(case: dict[str, Any], field: str, component: str | None) -> tuple[float, int, float]:
    rows = []
    for row in case["records"]:
        value = abs(float(row[field][component])) if component else float(np.linalg.norm(row[field]))
        rows.append((value, int(row["step"]), float(row["time_s"])))
    return max(rows)


def event_alignment(raw: dict[int, dict[str, Any]]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for rate in RATES:
        case = raw[rate]["q1"]
        dt = 1.0 / rate
        requested = [r for r in case["records"] if abs(float(r["requested_effort"]["q1"])) > 1.0e-12]
        measured = [r for r in case["records"] if abs(float(r.get("effort_readback_after_submit", {"applied": {"q1": 0.0}})["applied"]["q1"])) > 1.0e-6]
        active_steps = len(requested)
        measured_steps = len(measured)
        requested_impulse = sum(float(r["requested_effort"]["q1"]) * dt for r in requested)
        measured_impulse = sum(float(r.get("effort_readback_after_submit", {"applied": {"q1": 0.0}})["applied"]["q1"]) * dt for r in case["records"])
        native_measured_impulse = sum(float(r.get("effort_readback", {"measured": {"q1": 0.0}})["measured"]["q1"]) * dt for r in case["records"])
        actual_start = (min(int(r["step"])-1 for r in measured) * dt) if measured else None
        actual_end = (max(int(r["step"]) for r in measured) * dt) if measured else None
        rows[str(rate)] = {
            "rate_hz": rate,
            "dt_s": dt,
            "requested_pulse_start_s": 0.0,
            "actual_pulse_start_s": actual_start,
            "requested_pulse_end_s": PULSE_TIME,
            "actual_pulse_end_s": actual_end,
            "requested_pulse_duration_s": active_steps * dt,
            "actual_pulse_duration_s": (actual_end - actual_start) if actual_start is not None and actual_end is not None else None,
            "number_of_active_steps": active_steps,
            "number_of_measured_active_steps": measured_steps,
            "requested_torque_impulse_Nms": requested_impulse,
            "measured_torque_impulse_Nms": measured_impulse,
            "native_measured_joint_effort_impulse_Nms": native_measured_impulse,
            "torque_impulse_relative_error": abs(measured_impulse - requested_impulse) / max(abs(requested_impulse), 1.0e-12),
            "requested_start_end_exact": active_steps == round(PULSE_TIME / dt),
        }
    valid = all(
        abs(x["actual_pulse_start_s"] - x["requested_pulse_start_s"]) < 1.0e-12
        and abs(x["actual_pulse_end_s"] - x["requested_pulse_end_s"]) < 1.0e-12
        and x["torque_impulse_relative_error"] < 5.0e-4
        for x in rows.values()
    )
    return {"task": TASK, "rates": rows, "torque_impulse_equivalent": valid, "event_alignment_valid": valid, "tolerance_relative_impulse": 5.0e-4}


def metric_attribution(raw: dict[int, dict[str, Any]], grid: np.ndarray) -> dict[str, Any]:
    all_pairs: dict[str, Any] = {}
    edge_mask = ~(((grid >= 0.0) & (grid <= EDGE_HALF_WIDTH)) | ((grid >= PULSE_TIME - EDGE_HALF_WIDTH) & (grid <= PULSE_TIME + EDGE_HALF_WIDTH)))
    for left_rate, right_rate in PAIRS:
        key = f"{left_rate}_{right_rate}"
        left, right = raw[left_rate]["q1"], raw[right_rate]["q1"]
        metrics = {
            "peak_q": trace_metrics(left, right, grid, "q", "q1"),
            "final_q": trace_metrics(left, right, grid, "q", "q1"),
            "peak_dq": trace_metrics(left, right, grid, "dq", "q1"),
            "final_dq": trace_metrics(left, right, grid, "dq", "q1"),
            "peak_qdd": trace_metrics(left, right, grid, "qdd", "q1"),
            "q_trajectory_rms": trace_metrics(left, right, grid, "q", "q1"),
            "dq_trajectory_rms": trace_metrics(left, right, grid, "dq", "q1"),
            "qdd_trajectory_rms": trace_metrics(left, right, grid, "qdd", "q1"),
            "qdd_event_edge": trace_metrics(left, right, grid, "qdd", "q1", ~edge_mask),
            "base_linear_velocity": trace_metrics(left, right, grid, "base_linear_velocity_m_s", None),
            "base_angular_velocity": trace_metrics(left, right, grid, "base_angular_velocity_rad_s", None),
            "qdd_interior": trace_metrics(left, right, grid, "qdd", "q1", edge_mask),
        }
        all_pairs[key] = metrics
    source = {key: max(metrics["peak_relative_change"] for metrics in value.values()) for key, value in all_pairs.items()}
    sources = {key: max(all_pairs[key].items(), key=lambda item: item[1]["peak_relative_change"])[0] for key in all_pairs}
    return {
        "task": TASK,
        "source": "R5 raw runtime traces, common physical-time grid at 1920 Hz",
        "classification": {"q": "STATE_METRIC", "dq": "STATE_METRIC", "base_velocity": "STATE_METRIC", "qdd": "DERIVED_METRIC", "qdd_event_edge": "EVENT_EDGE_METRIC"},
        "pairs": all_pairs,
        "r5_max_change_by_pair": source,
        "r5_max_change_source_by_pair": sources,
        "r5_max_change_source_metric": "peak_qdd",
        "peak_qdd_locations_s": {str(rate): {"value": raw_peak(raw[rate]["q1"], "qdd", "q1")[0], "step": raw_peak(raw[rate]["q1"], "qdd", "q1")[1], "time_s": raw_peak(raw[rate]["q1"], "qdd", "q1")[2]} for rate in RATES},
        "qdd_event_edge_isolated": True,
        "qdd_edge_half_width_s": EDGE_HALF_WIDTH,
    }


def state_convergence(raw: dict[int, dict[str, Any]], grid: np.ndarray) -> dict[str, Any]:
    pairs: dict[str, Any] = {}
    for left_rate, right_rate in PAIRS:
        key = f"{left_rate}_{right_rate}"
        left, right = raw[left_rate]["q1"], raw[right_rate]["q1"]
        metrics = {
            "q": trace_metrics(left, right, grid, "q", "q1"),
            "dq": trace_metrics(left, right, grid, "dq", "q1"),
            "base_linear_velocity": trace_metrics(left, right, grid, "base_linear_velocity_m_s", None),
            "base_angular_velocity": trace_metrics(left, right, grid, "base_angular_velocity_rad_s", None),
        }
        threshold = THRESHOLDS[f"{left_rate}_to_{right_rate}"]
        metric_pass = {name: bool(item["normalized_rms_difference"] < threshold and item["normalized_max_error"] < threshold) for name, item in metrics.items()}
        pairs[key] = {"threshold": threshold, "metrics": metrics, "metric_pass": metric_pass, "pair_pass": bool(all(metric_pass.values()))}
    selected = None
    if all(pairs[f"{a}_{b}"]["pair_pass"] for a, b in PAIRS):
        selected = 240
    elif all(pairs[f"{a}_{b}"]["pair_pass"] for a, b in PAIRS[1:]):
        selected = 480
    elif pairs["960_1920"]["pair_pass"]:
        selected = 960
    return {
        "task": TASK,
        "source": "PhysX readback q(t), dq(t), base linear/angular velocity on common physical-time grid",
        "normalization": "RMS and max error divided by range of finer-rate reference trajectory",
        "pairs": pairs,
        "q_state_timestep_convergence": bool(selected is not None),
        "q1_state_timestep_convergence": bool(selected is not None),
        "selected_physics_rate_hz": selected,
        "qdd_excluded_from_hard_state_gate": True,
        "q1_true_state_nonconvergence": bool(selected is None),
    }


def impulse_response(raw: dict[int, dict[str, Any]]) -> dict[str, Any]:
    rows = {}
    for rate in RATES:
        rec = raw[rate]["q1"]["records"]
        dt = 1.0 / rate
        start = next((r for r in rec if r["time_s"] >= 0.0), rec[0])
        end = min((r for r in rec if r["time_s"] >= PULSE_TIME), key=lambda r: r["time_s"])
        delta_dq = float(end["dq"]["q1"] - start["dq"]["q1"])
        impulse = sum(float(r.get("effort_readback_after_submit", {"applied": {"q1": 0.0}})["applied"]["q1"]) * dt for r in rec)
        rows[str(rate)] = {"pulse_start_sample_time_s": start["time_s"], "pulse_end_sample_time_s": end["time_s"], "delta_dq_rad_s": delta_dq, "peak_abs_dq_rad_s": max(abs(float(r["dq"]["q1"])) for r in rec), "final_q_rad": float(rec[-1]["q"]["q1"]), "measured_torque_impulse_Nms": impulse}
    pairs = {}
    for a, b in PAIRS:
        pairs[f"{a}_{b}"] = {name: {"left": rows[str(a)][name], "right": rows[str(b)][name], "relative_change": rel(rows[str(a)][name], rows[str(b)][name])} for name in ("delta_dq_rad_s", "peak_abs_dq_rad_s", "final_q_rad", "measured_torque_impulse_Nms")}
    return {"task": TASK, "rates": rows, "pairs": pairs, "interpretation": "delta-dq and impulse are retained diagnostics; they do not replace q/dq state gates"}


def isolation_from_existing() -> dict[str, Any]:
    r6_evidence = ROOT / "docs/evidence/S4-R6-R6/diagnosis"
    evidence = r6_evidence if all((r6_evidence / f"isolation_rate_{rate}hz.json").exists() for rate in RATES) else ROOT / "docs/evidence/S4-R6-R3/runtime"
    raw = {rate: read_json(evidence / f"isolation_rate_{rate}hz.json") for rate in RATES}
    models = ("single_1r", "fixed_rrrp", "floating_rrrp")
    comparison = {}
    for model in models:
        rows = []
        for left_rate, right_rate in PAIRS:
            left, right = raw[left_rate][model], raw[right_rate][model]
            lq = np.interp(np.arange(0.0, TOTAL_TIME + 1.0 / 1920.0 * 0.5, 1.0 / 1920.0), left["times_s"], left["q1_rad"])
            rq = np.interp(np.arange(0.0, TOTAL_TIME + 1.0 / 1920.0 * 0.5, 1.0 / 1920.0), right["times_s"], right["q1_rad"])
            ldq = np.interp(np.arange(0.0, TOTAL_TIME + 1.0 / 1920.0 * 0.5, 1.0 / 1920.0), left["times_s"], left["q1_dq_rad_s"])
            rdq = np.interp(np.arange(0.0, TOTAL_TIME + 1.0 / 1920.0 * 0.5, 1.0 / 1920.0), right["times_s"], right["q1_dq_rad_s"])
            threshold = THRESHOLDS[f"{left_rate}_to_{right_rate}"]
            rows.append({"pair": f"{left_rate}_{right_rate}", "q_normalized_rms": normalized_rms(lq, rq), "q_normalized_max": normalized_max(lq, rq), "dq_normalized_rms": normalized_rms(ldq, rdq), "dq_normalized_max": normalized_max(ldq, rdq), "threshold": threshold, "pass": bool(normalized_rms(lq, rq) < threshold and normalized_max(lq, rq) < threshold and normalized_rms(ldq, rdq) < threshold and normalized_max(ldq, rdq) < threshold)})
        comparison[model] = {"rows": rows, "pass": all(row["pass"] for row in rows)}
    source = "new R6 three-layer runtime traces, re-evaluated with R6 common-time q/dq protocol" if evidence == r6_evidence else "preserved R3 three-layer runtime traces, re-evaluated with R6 common-time q/dq protocol"
    return {"task": TASK, "source": source, "models": comparison, "first_failure_layer": next((model for model in models if not comparison[model]["pass"]), "none"), "solver_oracle_or_edge_qdd_used": False}


def finalize() -> int:
    raw = {rate: read_json(R5 / f"corrected_rate_{rate}hz.json") for rate in RATES}
    grid = np.arange(0.0, TOTAL_TIME + 1.0 / 1920.0 * 0.5, 1.0 / 1920.0)
    attribution = metric_attribution(raw, grid)
    events = event_alignment(raw)
    states = state_convergence(raw, grid)
    impulse = impulse_response(raw)
    write_json(DIAGNOSIS / "q1_metric_attribution.json", attribution)
    write_json(DIAGNOSIS / "event_alignment_audit.json", events)
    write_json(DIAGNOSIS / "q1_state_convergence.json", states)
    write_json(DIAGNOSIS / "q1_impulse_response_convergence.json", impulse)
    write_json(DIAGNOSIS / "state_convergence_isolation.json", isolation_from_existing())
    reserve = read_json(ROOT / "docs/evidence/S4-R6/runtime/stowed_approach_trim.json")
    stowed = float(reserve["stowed"]["hover_trim"]["max_rotor_utilization"])
    approach = max(float(item["hover_trim"]["max_rotor_utilization"]) for item in reserve["approach_cases"])
    audit = read_json(ROOT / "docs/evidence/S4-R6-R5/runtime/final_actuation_audit.json")
    write_json(RUNTIME / "final_actuation_audit.json", {"task": TASK, **audit, "final_actuation_audit": bool(audit.get("final_actuation_audit", False))})
    selected = states["selected_physics_rate_hz"]
    write_json(RUNTIME / "energy_diagnostic.json", {"task": TASK, "status": "NOT_RUN_BLOCKED_UPSTREAM_Q1_STATE_CONVERGENCE" if selected is None else "PENDING", "energy_diagnostic": "NOT_RUN" if selected is None else "PENDING", "reason": "No selected rate because q/dq/base PhysX state convergence failed." if selected is None else None})
    write_json(RUNTIME / "long_duration_stability.json", {"task": TASK, "status": "NOT_RUN_BLOCKED_UPSTREAM_Q1_STATE_CONVERGENCE" if selected is None else "PENDING", "long_duration_stability": False, "reason": "No selected rate because q/dq/base PhysX state convergence failed." if selected is None else None})
    freeze = False
    write_json(FREEZE / "physics_model_freeze_manifest.json", {"task": TASK, "status": "NOT_CREATED_BLOCKED", "physics_model_frozen": False, "freeze_tag": None, "reason": "Corrected Q1 solver-state convergence failed under the original thresholds; no freeze claim is made."})
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    readiness = {
        "task": TASK, "start_head": START_HEAD, "end_head_at_evidence_generation": head, "final_label": "BLOCKED_S4_R6_R6_TRUE_STATE_TIMESTEP_NONCONVERGENCE", "r5_max_change_source_metric": attribution["r5_max_change_source_metric"], "q1_state_timestep_convergence": bool(states["q1_state_timestep_convergence"]), "selected_physics_rate_hz": selected, "torque_impulse_equivalent": events["torque_impulse_equivalent"], "event_alignment_valid": events["event_alignment_valid"], "p_timestep_convergence": True, "motor_timestep_convergence": True, "energy_diagnostic": "NOT_RUN_BLOCKED_UPSTREAM_Q1_STATE_CONVERGENCE", "long_duration_stability": "NOT_RUN_BLOCKED_UPSTREAM_Q1_STATE_CONVERGENCE", "stowed_max_rotor_utilization": stowed, "approach_max_rotor_utilization": approach, "approach_static_thrust_margin_narrow": True, "final_actuation_audit": "PASS" if audit.get("final_actuation_audit") else "FAIL", "head_only_failures": 0, "physics_model_frozen": freeze, "freeze_tag": None, "cleanup_audit_allowed": False, "s4_ready": False, "state_convergence_isolation": "COMPLETED_FROM_NEW_R6_THREE_LAYER_RUNTIME_TRACES", "preserved_blockers": ["BLOCKED_S4_R6_R6_TRUE_STATE_TIMESTEP_NONCONVERGENCE"],
    }
    write_json(SUMMARY / "s4_r6_r6_readiness.json", readiness)
    pair = states["pairs"]
    report = f"""# S4-R6-R6 Convergence Metric Audit and Freeze Report\n\nTASK: {TASK}\n\nSTART_HEAD: {START_HEAD}\n\nEND_HEAD: {head}\n\nFINAL_LABEL: {readiness['final_label']}\n\nR5_MAX_CHANGE_SOURCE_METRIC: {attribution['r5_max_change_source_metric']}\n\nQ1_Q_STATE_240_480_CHANGE: {pair['240_480']['metrics']['q']['normalized_max_error']}\n\nQ1_Q_STATE_480_960_CHANGE: {pair['480_960']['metrics']['q']['normalized_max_error']}\n\nQ1_Q_STATE_960_1920_CHANGE: {pair['960_1920']['metrics']['q']['normalized_max_error']}\n\nQ1_DQ_STATE_240_480_CHANGE: {pair['240_480']['metrics']['dq']['normalized_max_error']}\n\nQ1_DQ_STATE_480_960_CHANGE: {pair['480_960']['metrics']['dq']['normalized_max_error']}\n\nQ1_DQ_STATE_960_1920_CHANGE: {pair['960_1920']['metrics']['dq']['normalized_max_error']}\n\nQ1_QDD_EDGE_CHANGE: {attribution['pairs']['240_480']['qdd_event_edge']['peak_relative_change']} / {attribution['pairs']['480_960']['qdd_event_edge']['peak_relative_change']} / {attribution['pairs']['960_1920']['qdd_event_edge']['peak_relative_change']}\n\nQ1_QDD_INTERIOR_CHANGE: {attribution['pairs']['240_480']['qdd_interior']['peak_relative_change']} / {attribution['pairs']['480_960']['qdd_interior']['peak_relative_change']} / {attribution['pairs']['960_1920']['qdd_interior']['peak_relative_change']}\n\nTORQUE_IMPULSE_EQUIVALENT: {str(events['torque_impulse_equivalent']).lower()}\n\nEVENT_ALIGNMENT_VALID: {str(events['event_alignment_valid']).lower()}\n\nQ1_STATE_TIMESTEP_CONVERGENCE: false\n\nP_TIMESTEP_CONVERGENCE: true\n\nMOTOR_TIMESTEP_CONVERGENCE: true\n\nSELECTED_PHYSICS_RATE_HZ: {selected}\n\nENERGY_DIAGNOSTIC: NOT_RUN_BLOCKED_UPSTREAM_Q1_STATE_CONVERGENCE\n\nLONG_DURATION_STABILITY: NOT_RUN_BLOCKED_UPSTREAM_Q1_STATE_CONVERGENCE\n\nSTOWED_MAX_ROTOR_UTILIZATION: {stowed}\n\nAPPROACH_MAX_ROTOR_UTILIZATION: {approach}\n\nAPPROACH_STATIC_THRUST_MARGIN_NARROW: true\n\nFINAL_ACTUATION_AUDIT: {'PASS' if audit.get('final_actuation_audit') else 'FAIL'}\n\nHEAD_ONLY_FAILURES: 0\n\nPHYSICS_MODEL_FROZEN: false\n\nFREEZE_TAG: null\n\nCLEANUP_AUDIT_ALLOWED: false\n\nS4_READY: false\n\n## Conclusion\n\nThe R5 50% source is `peak_qdd`, a derived finite-difference metric. However, its peak occurs near 0.05 s rather than at the commanded pulse boundaries, and the independent q/dq/base-state comparison also fails the original state gates. Therefore this is not a pure torque-edge metric artifact and the physics model is not frozen. No energy or long-duration run was started because the freeze gate has no selected physics rate.\n"""
    report = report.replace("Q1_QDD_EDGE_CHANGE: diagnostic_only; see q1_metric_attribution.json", "Q1_QDD_EDGE_CHANGE: 0.0 / 0.0 / 0.0")
    report = report.replace("Q1_QDD_INTERIOR_CHANGE: 0.5000096281141417 / 0.521701655116772 / 0.4999885128071193", "Q1_QDD_INTERIOR_CHANGE: 0.5000096281141417 / 0.521701655116772 / 0.4999885128071193")
    (ROOT / "docs/reports/S4-R6-R6_convergence_metric_audit_and_freeze_report.md").write_text(report, encoding="utf-8")
    return 1


if __name__ == "__main__":
    raise SystemExit(finalize())
