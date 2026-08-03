"""Write frozen S2-R6 barrier configurations after baseline calibration."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

from planner_bridge.execution.playback_validator import sample_raw


ROOT = Path(__file__).resolve().parents[2]
ANCHOR = ROOT / "docs/evidence/S2-R6/envelope/anchor_balls.json"
RUN = ROOT / "docs/evidence/S2-R6/runtime/round1_disabled"
OUT = ROOT / "docs/evidence/S2-R6/configs"
BASELINE_ARM_JERK_COST = 0.3282412784949961


def main() -> None:
    anchor = json.loads(ANCHOR.read_text(encoding="utf-8"))
    arm = sample_raw(RUN / "trajectory_arm.json", 2000, arm=True)
    centers = np.asarray(anchor["centers_m"], dtype=float)
    radii = np.asarray(anchor["radii_m"], dtype=float)
    tau = float(anchor["tau0"])
    positions = np.asarray(arm["position"], dtype=float)
    z = radii[None, :] ** 2 - ((positions[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    logits = z / tau
    maximum = logits.max(axis=1)
    g = tau * (maximum + np.log(np.exp(logits - maximum[:, None]).mean(axis=1)))
    violation = np.maximum(0.0, -g)
    dt = np.gradient(np.asarray(arm["time"], dtype=float))
    integral_v3 = float(np.sum(dt * violation**3))
    w0 = float(0.01 * BASELINE_ARM_JERK_COST / integral_v3)
    calibration = {
        "baseline_run": "docs/evidence/S2-R6/runtime/round1_disabled",
        "baseline_final_cost_from_roslaunch": 3038.323,
        "baseline_arm_jerk_cost_from_exported_coefficients": BASELINE_ARM_JERK_COST,
        "analysis_sample_hz": 2000,
        "adaptive_dt_s": 0.0005,
        "raw_barrier_min_g": float(g.min()),
        "raw_barrier_max_violation": float(violation.max()),
        "raw_barrier_active_samples": int(np.count_nonzero(violation > 0.0)),
        "raw_integral_v3_s": integral_v3,
        "tau0": tau,
        "w0": w0,
        "target_initial_barrier_cost": float(w0 * integral_v3),
        "target_fraction_of_baseline_arm_jerk": 0.01,
        "weight_candidates": {"w0": w0, "10w0": 10.0 * w0, "100w0": 100.0 * w0},
        "selection_rule": "first candidate passing joint, clearance, and direction hard gates; no tau sweep",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/evidence/S2-R6/calibration.json").write_text(json.dumps(calibration, indent=2) + "\n", encoding="utf-8")
    for label, weight in (("w0", w0), ("10w0", 10.0 * w0), ("100w0", 100.0 * w0)):
        config = {
            "UseExecutionEnvelopeBarrier": True,
            "ExecutionEnvelopeWeight": float(weight),
            "ExecutionEnvelopeTau": tau,
            "ExecutionEnvelopeCenters": [float(value) for row in centers.tolist() for value in row],
            "ExecutionEnvelopeRadii": [float(value) for value in radii.tolist()],
            "ExecutionEnvelopeDiagnostics": True,
        }
        (OUT / f"s2_r6_{label}.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    print(json.dumps(calibration, indent=2))


if __name__ == "__main__":
    main()
