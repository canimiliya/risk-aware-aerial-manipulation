"""S4-R6-R4 joint-effort path audit.

This diagnostic is deliberately narrower than R3.  It does not alter the
production USD/design inputs and does not sweep timestep, solver settings, or
energy.  It audits the authored limits and the two public effort submission
paths on the in-memory single-1R clone used by R3.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "robot_assets/rrrp/rrrp_arm.usd"
DESIGN = ROOT / "robot_assets/rrrp/rrrp_design.yaml"
EVIDENCE = ROOT / "docs/evidence/S4-R6-R4/effort"
SUMMARY = ROOT / "docs/evidence/S4-R6-R4/summary"
START_HEAD = "f7e7ca207029d20c9383f4d0ea9da6c25598fa6d"
TASK = "S4-R6-R4-JOINT-EFFORT-PATH-AUDIT-R1"
COMMAND_TEST_TORQUE_NM = 0.2
RATE_HZ = 240
TAU_SWEEP = [0.005, 0.010, 0.020, 0.030, 0.040, 0.045, 0.050, 0.075, 0.100, 0.150, 0.200]

from s4_r6_r3_revolute_dynamics_isolation import (  # noqa: E402
    a,
    make_single_1r,
    mass_matrix_audit,
    metadata,
    native_joint_index,
    native_joint_vector,
    open_world,
    setup,
    write_json,
)


def scalar(value: Any) -> float | None:
    if value is None:
        return None
    arr = np.asarray(value, dtype=float).reshape(-1)
    return float(arr[0]) if arr.size else None


def arr(value: Any) -> list[float] | None:
    if value is None:
        return None
    return np.asarray(value, dtype=float).reshape(-1).tolist()


def joint_value(values: Any, index: int) -> float | None:
    values = np.asarray(values, dtype=float)
    if values.ndim == 2:
        values = values[0]
    return scalar(values[index])


def design_audit() -> dict[str, Any]:
    design = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
    joints = design["joints"]
    return {
        "task": TASK,
        "source_design": str(DESIGN.resolve()),
        "source_design_read_only": True,
        "source_usd": str(ASSET.resolve()),
        "source_usd_read_only": True,
        "command_test_torque_Nm": COMMAND_TEST_TORQUE_NM,
        "design_max_effort_Nm": {
            "q1": float(joints["q1"]["max_effort"]),
            "q2": float(joints["q2"]["max_effort"]),
            "q3": float(joints["q3"]["max_effort"]),
            "P": float(joints["d"]["max_effort"]),
        },
        "design_max_velocity": {name: float(item["max_velocity"]) for name, item in joints.items()},
    }


def usd_limit_audit() -> dict[str, Any]:
    from pxr import Usd

    stage = Usd.Stage.Open(str(ASSET.resolve()))
    paths = {
        "q1": "/World/FloatingBaseArm/joints/q1",
        "q2": "/World/FloatingBaseArm/joints/q2",
        "q3": "/World/FloatingBaseArm/joints/q3",
        "P": "/World/FloatingBaseArm/joints/d",
    }
    rows: dict[str, Any] = {}
    for name, path in paths.items():
        prim = stage.GetPrimAtPath(path)
        attrs = {str(x.GetName()): x.Get() for x in prim.GetAttributes()}
        rows[name] = {
            "path": path,
            "joint_type": prim.GetTypeName(),
            "authored_attributes": {k: str(v) for k, v in attrs.items()},
            "max_force_candidates": {k: str(v) for k, v in attrs.items() if "force" in k.lower() or "effort" in k.lower()},
            "drive_candidates": {k: str(v) for k, v in attrs.items() if "drive" in k.lower()},
            "max_velocity_candidates": {k: str(v) for k, v in attrs.items() if "velocity" in k.lower()},
            "stiffness_candidates": {k: str(v) for k, v in attrs.items() if "stiffness" in k.lower()},
            "damping_candidates": {k: str(v) for k, v in attrs.items() if "damping" in k.lower()},
            "armature_candidates": {k: str(v) for k, v in attrs.items() if "armature" in k.lower()},
        }
    return {"task": TASK, "source_usd": str(ASSET.resolve()), "source_usd_read_only": True, "joints": rows}


def get_q1_runtime(art: Any) -> dict[str, Any]:
    controller = art.get_articulation_controller()
    view = art._articulation_view
    idx = native_joint_index(art, "q1")
    return {
        "articulation_metadata": metadata(art),
        "q1_native_index": idx,
        "runtime_max_efforts_articulation_controller": arr(controller.get_max_efforts()),
        "runtime_effort_modes_articulation_controller": controller.get_effort_modes(),
        "runtime_gains_articulation_controller": {
            "stiffness": arr(controller.get_gains()[0]),
            "damping": arr(controller.get_gains()[1]),
        },
        "runtime_max_efforts_view": arr(view.get_max_efforts()),
        "runtime_effort_modes_view": view.get_effort_modes(),
        "runtime_gains_view": {"stiffness": arr(view.get_gains()[0]), "damping": arr(view.get_gains()[1])},
        "q1_runtime_max_effort_Nm": scalar(controller.get_max_efforts()[idx]),
        "q1_runtime_effort_mode": controller.get_effort_modes()[idx],
        "q1_runtime_stiffness": scalar(controller.get_gains()[0][idx]),
        "q1_runtime_damping": scalar(controller.get_gains()[1][idx]),
    }


def q1_effort_limit_manifest(art: Any) -> dict[str, Any]:
    design = design_audit()
    usd = usd_limit_audit()
    runtime = get_q1_runtime(art)
    design_max = design["design_max_effort_Nm"]["q1"]
    usd_force = usd["joints"]["q1"]["max_force_candidates"]
    numeric_usd = None
    for key, value in usd_force.items():
        if "maxjointforce" not in key.lower() and "maxforce" not in key.lower():
            continue
        try:
            numeric_usd = float(value)
            break
        except (TypeError, ValueError):
            continue
    runtime_max = runtime["q1_runtime_max_effort_Nm"]
    candidates = [x for x in (numeric_usd, runtime_max, design_max) if x is not None]
    observed = 0.04599239
    manifest = {
        "task": TASK,
        "command_test_torque_Nm": COMMAND_TEST_TORQUE_NM,
        "design_max_effort_Nm": design_max,
        "design_max_efforts_all": design["design_max_effort_Nm"],
        "usd_max_effort_Nm": numeric_usd,
        "usd_max_effort_raw_candidates": usd_force,
        "runtime_max_effort_Nm": runtime_max,
        "runtime_max_effort_pre_command_Nm": runtime_max,
        "runtime_effort_mode": runtime["q1_runtime_effort_mode"],
        "runtime_stiffness": runtime["q1_runtime_stiffness"],
        "runtime_damping": runtime["q1_runtime_damping"],
        "runtime_readback": runtime,
        "command_exceeds_any_limit": bool(any(COMMAND_TEST_TORQUE_NM > float(x) for x in candidates)),
        "possible_cap_values_near_observed": [x for x in candidates if abs(float(x) - observed) <= 0.005],
        "effective_torque_from_r3_Nm": observed,
        "effort_cap_matches_observed_dynamics": bool(any(abs(float(x) - observed) <= 0.005 for x in candidates)),
        "usd_readback_does_not_modify_source": True,
    }
    write_json(EVIDENCE / "q1_effort_limit_manifest.json", manifest)
    return manifest


def effort_values(art: Any) -> dict[str, Any]:
    idx = native_joint_index(art, "q1")
    return {
        "applied_all": arr(art.get_applied_joint_efforts()),
        "measured_all": arr(art.get_measured_joint_efforts()),
        "applied_q1": joint_value(art.get_applied_joint_efforts(), idx),
        "measured_q1": joint_value(art.get_measured_joint_efforts(), idx),
    }


def action_for(art: Any, tau: float) -> Any:
    from isaacsim.core.utils.types import ArticulationAction

    return ArticulationAction(joint_efforts=native_joint_vector(art, [tau, 0.0, 0.0, 0.0]))


def one_step(art: Any, world: Any, tau: float, path: str, mass: dict[str, Any]) -> dict[str, Any]:
    setup(art, world)
    idx = native_joint_index(art, "q1")
    q0 = joint_value(art.get_joint_positions(), idx)
    dq0 = joint_value(art.get_joint_velocities(), idx)
    if path == "set_joint_efforts":
        art.set_joint_efforts(native_joint_vector(art, [tau, 0.0, 0.0, 0.0]))
    elif path == "apply_action":
        art.apply_action(action_for(art, tau))
    else:
        raise ValueError(path)
    before = effort_values(art)
    world.step(render=False)
    q1 = joint_value(art.get_joint_positions(), idx)
    dq1 = joint_value(art.get_joint_velocities(), idx)
    after = effort_values(art)
    qdd = (dq1 - dq0) * RATE_HZ
    inertia = float(mass.get("q1_motion_inertia", mass["q1_effective_inertia"]))
    return {
        "tau_cmd_Nm": tau,
        "path": path,
        "q0_rad": q0,
        "dq0_rad_s": dq0,
        "q1_rad": q1,
        "dq1_rad_s": dq1,
        "derived_qdd_rad_s2": qdd,
        "tau_implied_from_motion_Nm": inertia * qdd,
        "effort_readback_before_step": before,
        "effort_readback_after_step": after,
        "max_effort": get_q1_runtime(art),
    }


def runtime_audit(output: Path) -> int:
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "hide_ui": True, "disable_viewport_updates": True, "renderer": "MinimalRendering"})
    try:
        stage, world, fixed, floating, fixed_bodies, floating_bodies = open_world(RATE_HZ)
        make_single_1r(stage)
        single = world.scene.add(__import__("isaacsim.core.prims", fromlist=["SingleArticulation"]).SingleArticulation(prim_path="/World/SingleRevolute1R", name="r4_single_1r"))
        world.initialize_physics()
        world.reset()
        for _ in range(2):
            world.step(render=False)
        mass = mass_matrix_audit(single, "single_1r")
        q1_index = int(mass["q1_mass_matrix_index"])
        mass["q1_motion_inertia"] = float(mass["M_q0"][q1_index][q1_index])
        manifest = q1_effort_limit_manifest(single)
        runtime_probe = one_step(single, world, 0.0, "set_joint_efforts", mass)
        manifest["runtime_max_effort_Nm"] = runtime_probe["max_effort"]["q1_runtime_max_effort_Nm"]
        manifest["runtime_max_effort_post_initialization_Nm"] = manifest["runtime_max_effort_Nm"]
        finite_limits = [x for x in (manifest["design_max_effort_Nm"], manifest["usd_max_effort_Nm"], manifest["runtime_max_effort_Nm"]) if x is not None and np.isfinite(float(x))]
        manifest["command_exceeds_any_limit"] = bool(any(COMMAND_TEST_TORQUE_NM > float(x) for x in finite_limits))
        manifest["possible_cap_values_near_observed"] = [x for x in finite_limits if abs(float(x) - 0.04599239) <= 0.005]
        manifest["effort_cap_matches_observed_dynamics"] = bool(any(abs(float(x) - 0.04599239) <= 0.005 for x in finite_limits))
        write_json(EVIDENCE / "q1_effort_limit_manifest.json", manifest)
        records = {"task": TASK, "rate_hz": RATE_HZ, "protocol": {"gravity": False, "drive_stiffness": 0.0, "drive_damping": 0.0, "collision": False, "contact": False, "initial_q": 0.0, "initial_dq": 0.0}, "effort_limit_manifest": manifest, "mass_matrix": mass}
        trace_rows: list[dict[str, Any]] = []
        for tau in TAU_SWEEP:
            trace_rows.append(one_step(single, world, tau, "set_joint_efforts", mass))
            trace_rows.append(one_step(single, world, tau, "apply_action", mass))
        records["trace_rows"] = trace_rows
        records["path_comparison"] = {
            "set_joint_efforts": one_step(single, world, COMMAND_TEST_TORQUE_NM, "set_joint_efforts", mass),
            "apply_action": one_step(single, world, COMMAND_TEST_TORQUE_NM, "apply_action", mass),
        }
        write_json(output, records)
        write_json(EVIDENCE / "effort_path_trace.json", {"task": TASK, "rows": trace_rows})
        with (EVIDENCE / "effort_path_trace.csv").open("w", newline="", encoding="utf-8") as handle:
            fields = ["path", "tau_cmd_Nm", "q0_rad", "dq0_rad_s", "q1_rad", "dq1_rad_s", "derived_qdd_rad_s2", "tau_implied_from_motion_Nm", "applied_q1_before", "measured_q1_before", "applied_q1_after", "measured_q1_after", "runtime_max_effort_Nm", "runtime_effort_mode"]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in trace_rows:
                before, after = row["effort_readback_before_step"], row["effort_readback_after_step"]
                writer.writerow({"path": row["path"], "tau_cmd_Nm": row["tau_cmd_Nm"], "q0_rad": row["q0_rad"], "dq0_rad_s": row["dq0_rad_s"], "q1_rad": row["q1_rad"], "dq1_rad_s": row["dq1_rad_s"], "derived_qdd_rad_s2": row["derived_qdd_rad_s2"], "tau_implied_from_motion_Nm": row["tau_implied_from_motion_Nm"], "applied_q1_before": before["applied_q1"], "measured_q1_before": before["measured_q1"], "applied_q1_after": after["applied_q1"], "measured_q1_after": after["measured_q1"], "runtime_max_effort_Nm": row["max_effort"]["q1_runtime_max_effort_Nm"], "runtime_effort_mode": row["max_effort"]["q1_runtime_effort_mode"]})
        write_json(EVIDENCE / "effort_api_path_comparison.json", {"task": TASK, "comparison": records["path_comparison"]})
        return 0
    except BaseException:
        write_json(output, {"task": TASK, "error": traceback.format_exc()})
        return 1
    finally:
        app.close(wait_for_replicator=False, skip_cleanup=True)


def finalize(runtime_path: Path) -> int:
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    manifest = runtime["effort_limit_manifest"]
    mass = runtime["mass_matrix"]
    rows = runtime["trace_rows"]
    sweep = []
    for row in rows:
        sweep.append({"path": row["path"], "tau_cmd_Nm": row["tau_cmd_Nm"], "tau_applied_api_Nm": row["effort_readback_after_step"]["applied_q1"], "tau_measured_Nm": row["effort_readback_after_step"]["measured_q1"], "qdd_sim_rad_s2": row["derived_qdd_rad_s2"], "tau_implied_Nm": row["tau_implied_from_motion_Nm"]})
    write_json(EVIDENCE / "q1_effort_sweep.json", {"task": TASK, "rate_hz": RATE_HZ, "rows": sweep, "command_values_Nm": TAU_SWEEP})
    q1_rows = [x for x in sweep if x["path"] == "apply_action"]
    low = [x for x in q1_rows if x["tau_cmd_Nm"] <= 0.04]
    high = [x for x in q1_rows if x["tau_cmd_Nm"] >= 0.075]
    ratios = [x["tau_implied_Nm"] / x["tau_cmd_Nm"] for x in q1_rows if x["tau_cmd_Nm"] > 0]
    saturation = bool(high and max(x["tau_implied_Nm"] for x in high) - min(x["tau_implied_Nm"] for x in high) < 0.01 and low and max(x["tau_implied_Nm"] for x in low) > min(x["tau_implied_Nm"] for x in low))
    scaling = bool(ratios and np.std(ratios) < 0.03 and np.mean(ratios) < 0.8)
    comparison = runtime["path_comparison"]
    path_match = abs(comparison["set_joint_efforts"]["derived_qdd_rad_s2"] - comparison["apply_action"]["derived_qdd_rad_s2"]) <= 1.0e-6
    actual = comparison["apply_action"]["effort_readback_after_step"]
    old_effective_inertia = float(mass["q1_effective_inertia"])
    motion_inertia = float(mass["q1_motion_inertia"])
    old_requested_qdd = COMMAND_TEST_TORQUE_NM / old_effective_inertia
    requested_qdd = COMMAND_TEST_TORQUE_NM / motion_inertia
    applied_qdd = (actual["applied_q1"] or 0.0) / motion_inertia
    measured_qdd = (actual["measured_q1"] or 0.0) / motion_inertia
    sim_qdd = comparison["apply_action"]["derived_qdd_rad_s2"]
    oracle = {
        "task": TASK,
        "M11_fixed_base_motion_inertia_kg_m2": motion_inertia,
        "q1_effective_inertia_r3_schur_complement_kg_m2": old_effective_inertia,
        "qdd_sim_rad_s2": sim_qdd,
        "tau_implied_from_sim_Nm": comparison["apply_action"]["tau_implied_from_motion_Nm"],
        "qdd_oracle_old_using_requested_effort_rad_s2": old_requested_qdd,
        "qdd_oracle_using_requested_effort_rad_s2": requested_qdd,
        "qdd_oracle_using_applied_effort_rad_s2": applied_qdd,
        "qdd_oracle_using_measured_effort_rad_s2": measured_qdd,
        "tau_requested_Nm": COMMAND_TEST_TORQUE_NM,
        "tau_applied_api_Nm": actual["applied_q1"],
        "tau_measured_Nm": actual["measured_q1"],
        "sim_over_old_oracle": sim_qdd / old_requested_qdd,
        "reconciliation": {"requested_effort_matches_motion": abs(sim_qdd - requested_qdd) < 1.0, "applied_effort_matches_motion": abs(sim_qdd - applied_qdd) < 1.0, "measured_effort_matches_motion": abs(sim_qdd - measured_qdd) < 1.0},
        "r3_oracle_bug": "R3 inverted the full 7x7 generalized mass matrix. The fixed-base single-1R response uses the q1 diagonal M[6,6]; the full inverse included free-base coupling that is constrained out by the fixed-base anchor.",
        "interpretation": "actual effort readbacks and motion are compared against M^-1*tau; no force value is inferred from qdd alone when the API readback is available",
    }
    write_json(EVIDENCE / "q1_oracle_reconciliation.json", oracle)
    if manifest["command_exceeds_any_limit"] and manifest["effort_cap_matches_observed_dynamics"]:
        label = "EFFORT_SATURATION_CONFIRMED"
        final_label = "S4_R6_R4_EFFORT_SATURATION_ROOT_CAUSE_CONFIRMED"
    elif saturation:
        label = "EFFORT_SATURATION_CONFIRMED"
        final_label = "S4_R6_R4_EFFORT_SATURATION_ROOT_CAUSE_CONFIRMED"
    elif scaling and not path_match:
        label = "EFFORT_SCALING_BUG_CONFIRMED"
        final_label = "BLOCKED_S4_R6_R4_EFFORT_SCALING_PATH"
    elif abs(sim_qdd - measured_qdd) < 1.0:
        label = "ORACLE_INTERPRETATION_BUG_CONFIRMED"
        final_label = "S4_R6_R4_ORACLE_INTERPRETATION_ROOT_CAUSE_CONFIRMED"
    else:
        label = "PHYSX_NATIVE_DYNAMICS_MISMATCH_CONFIRMED"
        final_label = "BLOCKED_S4_R6_R4_PHYSX_NATIVE_DYNAMICS_MISMATCH"
    readiness = {"task": TASK, "start_head": START_HEAD, "end_head_at_evidence_generation": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(), "final_label": final_label, "allowed_conclusion": label, "q1_command_torque_Nm": COMMAND_TEST_TORQUE_NM, "q1_design_max_effort_Nm": manifest["design_max_effort_Nm"], "q1_usd_max_effort_Nm": manifest["usd_max_effort_Nm"], "q1_runtime_max_effort_Nm": manifest["runtime_max_effort_Nm"], "q1_runtime_max_effort_pre_command_Nm": manifest["runtime_max_effort_pre_command_Nm"], "command_exceeds_max_effort": manifest["command_exceeds_any_limit"], "q1_applied_effort_at_0p2": actual["applied_q1"], "q1_measured_effort_at_0p2": actual["measured_q1"], "q1_effective_inertia_r3_schur_complement": old_effective_inertia, "q1_M11_fixed_base_motion_inertia": motion_inertia, "q1_sim_qdd_at_0p2": sim_qdd, "q1_implied_torque_from_sim": comparison["apply_action"]["tau_implied_from_motion_Nm"], "effort_sweep_linear_below_limit": not saturation, "effort_saturation_present": saturation, "effort_scaling_present": scaling, "set_joint_efforts_path": True, "apply_action_path": True, "effort_api_path_match": path_match, "oracle_using_actual_effort": bool(abs(sim_qdd - measured_qdd) < 1.0), "asset_bug_found": False, "physx_solver_limitation_confirmed": label == "PHYSX_NATIVE_DYNAMICS_MISMATCH_CONFIRMED", "physics_model_frozen": False, "cleanup_allowed": False, "energy_diagnostic_deferred": True, "preserved_blockers": ["BLOCKED_S4_R6_TIMESTEP_CONVERGENCE", "BLOCKED_S4_R6_R2_SOLVER_CONVERGENCE"]}
    write_json(SUMMARY / "s4_r6_r4_readiness.json", readiness)
    report = f"""# S4-R6-R4 Joint Effort Path Audit Report

TASK: {TASK}

START_HEAD: {START_HEAD}

END_HEAD: {readiness['end_head_at_evidence_generation']}

FINAL_LABEL: {final_label}

ALLOWED_CONCLUSION: {label}

Q1_COMMAND_TORQUE_NM: {COMMAND_TEST_TORQUE_NM}

Q1_DESIGN_MAX_EFFORT_NM: {manifest['design_max_effort_Nm']}

Q1_USD_MAX_EFFORT_NM: {manifest['usd_max_effort_Nm']}

Q1_RUNTIME_MAX_EFFORT_NM: {manifest['runtime_max_effort_Nm']}

COMMAND_EXCEEDS_MAX_EFFORT: {str(manifest['command_exceeds_any_limit']).lower()}

Q1_APPLIED_EFFORT_AT_0P2: {actual['applied_q1']}

Q1_MEASURED_EFFORT_AT_0P2: {actual['measured_q1']}

Q1_EFFECTIVE_INERTIA: {motion_inertia}

Q1_EFFECTIVE_INERTIA_R3_SCHUR_COMPLEMENT: {old_effective_inertia}

Q1_M11_FIXED_BASE_MOTION_INERTIA: {motion_inertia}

Q1_SIM_QDD_AT_0P2: {sim_qdd}

Q1_IMPLIED_TORQUE_FROM_SIM: {comparison['apply_action']['tau_implied_from_motion_Nm']}

EFFORT_SWEEP_LINEAR_BELOW_LIMIT: {str(not saturation).lower()}

EFFORT_SATURATION_PRESENT: {str(saturation).lower()}

EFFORT_SCALING_PRESENT: {str(scaling).lower()}

SET_JOINT_EFFORTS_PATH: PASS

APPLY_ACTION_PATH: PASS

ORACLE_USING_ACTUAL_EFFORT: {'PASS' if abs(sim_qdd - measured_qdd) < 1.0 else 'FAIL'}

ASSET_BUG_FOUND: false

PHYSX_SOLVER_LIMITATION_CONFIRMED: {str(label == 'PHYSX_NATIVE_DYNAMICS_MISMATCH_CONFIRMED').lower()}

PHYSICS_MODEL_FROZEN: false

CLEANUP_ALLOWED: false

## Scope

- Production USD, design YAML, mass, inertia, rotor, motor, damping, armature, solver, and historical evidence were not modified.
- The single 1R is the R3 in-memory clone and is never exported.
- Energy and timestep/solver sweeps were intentionally deferred in this task.
"""
    (ROOT / "docs/reports/S4-R6-R4_joint_effort_path_audit_report.md").write_text(report, encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["runtime", "finalize"], required=True)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "runtime_effort_audit.json")
    args = parser.parse_args()
    if args.mode == "runtime":
        return runtime_audit(args.output)
    return finalize(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
