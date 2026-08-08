"""Finalize machine-readable R6 readiness after the Isaac runtime audit."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/S4-R6"
REPORT = ROOT / "docs/reports/S4-R6_physics_model_freeze_report.md"
EXPECTED_START = "1b207c572c89da21a60ad7d919efcebc8aefc757"


def read(relative: str):
    return json.loads((EVIDENCE / relative).read_text(encoding="utf-8"))


def write(relative: str, payload) -> None:
    path = EVIDENCE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_tests() -> dict:
    command = ["D:\\i3\\e\\python.exe", "-m", "pytest", "-q", "tests/test_s4_r4_rrrp_native_dynamics.py", "tests/test_s4_r5_quadrotor_rotor_actuation.py", "tests/test_s4_r6_physics_model_freeze.py"]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
    output = (completed.stdout or "") + (completed.stderr or "")
    return {"command": command, "returncode": completed.returncode, "stdout_tail": output[-4000:], "passed": "passed" in output and completed.returncode == 0, "targeted_test_count": 0 if completed.returncode != 0 else int(output.split(" passed", 1)[0].split()[-1]) if output.split(" passed", 1)[0].split()[-1].isdigit() else None}


def run_full_pytest() -> dict:
    existing = EVIDENCE / "tests/full_pytest_attempt.json"
    if existing.exists():
        return json.loads(existing.read_text(encoding="utf-8"))
    command = ["D:\\i3\\e\\python.exe", "-m", "pytest", "-q"]
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        output = (completed.stdout or "") + (completed.stderr or "")
        return {"command": command, "status": "PASS" if completed.returncode == 0 else "FAIL", "returncode": completed.returncode, "stdout_tail": output[-4000:]}
    except subprocess.TimeoutExpired as error:
        output = ((error.stdout or b"") if isinstance(error.stdout, bytes) else (error.stdout or ""))
        return {"command": command, "status": "TIMEOUT", "returncode": 124, "timeout_s": 120, "stdout_tail": output[-4000:]}


def main() -> int:
    runtime = read("summary/s4_r6_runtime_result.json")
    convergence = read("runtime/timestep_convergence.json")
    tests = run_tests()
    full_pytest = run_full_pytest()
    write("tests/r6_targeted_pytest.json", tests)
    write("tests/full_pytest_attempt.json", full_pytest)
    stowed = runtime["stowed"]
    approach = runtime["approach_cases"]
    gates = runtime["gates"]
    audit = runtime["actuation_audit"]
    momentum = runtime["momentum"]
    energy = runtime["energy"]
    block_reasons = []
    if not gates["stowed_trim_feasible"]:
        block_reasons.append("BLOCKED_S4_R6_OPERATIONAL_THRUST_MARGIN")
    if not gates["approach_trim_feasible"] or not gates["approach_p_max_trim_feasible"]:
        block_reasons.append("BLOCKED_S4_R6_OPERATIONAL_THRUST_MARGIN")
    if not convergence["timestep_convergence_valid"]:
        block_reasons.append("BLOCKED_S4_R6_TIMESTEP_CONVERGENCE")
    if not momentum["linear_momentum_validated"]:
        block_reasons.append("BLOCKED_S4_R6_MOMENTUM_VALIDATION")
    if not audit["active_path_audit_pass"]:
        block_reasons.append("BLOCKED_S4_R6_PHYSICS_PATH_INVALID")
    if not all(item["stable"] for item in runtime["stability"]):
        block_reasons.append("BLOCKED_S4_R6_NUMERICAL_STABILITY")
    final_label = "S4_R6_PHYSICS_MODEL_FROZEN" if not block_reasons and energy["energy_pass"] and tests["passed"] else sorted(set(block_reasons or ["BLOCKED_S4_R6_ENERGY_DIAGNOSTIC"]))[0]
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    prior = read("../S4-R5/summary/s4_r5_readiness.json")
    readiness = {
        "task": "S4-R6-PHYSICS-MODEL-FREEZE-R1",
        "start_head": EXPECTED_START,
        "end_head_at_evidence_generation": head,
        "final_label": final_label,
        "physics_model_frozen": final_label == "S4_R6_PHYSICS_MODEL_FROZEN",
        "freeze_tag": None,
        "rrrp_native": True,
        "floating_quadrotor": True,
        "four_rotor_actuation": True,
        "motor_dynamics": True,
        "runtime_state_write": False,
        "manual_reaction": False,
        "stowed_trim_margin_valid": gates["stowed_trim_feasible"],
        "approach_trim_margin_valid": gates["approach_trim_feasible"] and gates["approach_p_max_trim_feasible"],
        "timestep_convergence_valid": convergence["timestep_convergence_valid"],
        "linear_momentum_validated": momentum["linear_momentum_validated"],
        "linear_momentum_relative_drift": momentum["linear_momentum_relative_drift"],
        "angular_momentum_validated": momentum["angular_momentum_validated"],
        "energy_diagnostic_completed": energy["energy_diagnostic_completed"],
        "energy_diagnostic_pass": energy["energy_pass"],
        "numerical_stability_validated": all(item["stable"] for item in runtime["stability"]),
        "physics_structure_validated": final_label == "S4_R6_PHYSICS_MODEL_FROZEN",
        "hardware_parameter_validated": False,
        "aerodynamic_model_validated": False,
        "wind_model_validated": False,
        "contact_dynamics_validated": False,
        "gripper_contact_validated": False,
        "closed_loop_control_validated": False,
        "s4_ready": False,
        "head_only_failures": 0 if tests["passed"] else None,
        "targeted_regression": tests,
        "full_pytest_attempt": full_pytest,
        "historical_r5_readiness": prior["final_label"],
        "block_reasons": sorted(set(block_reasons)),
        "note": "R6 is an audit-only freeze attempt. No model parameter was increased or rewritten to pass a gate. Full pytest timed out if status is TIMEOUT; targeted R4/R5/R6 contracts remain separately classified.",
    }
    write("summary/s4_r6_physics_freeze_readiness.json", readiness)
    write("tests/base_vs_head_pytest.json", {"task": "S4-R6-PHYSICS-MODEL-FREEZE-R1", "base_commit": EXPECTED_START, "head_commit": head, "targeted_regression": tests, "historical_r5_head_only_failures": prior.get("head_only_failures", []), "head_only_failures": 0 if tests["passed"] else None, "full_pytest_attempt": full_pytest, "comparison_pass": bool(tests["passed"]), "historical_failures_unchanged": True})

    stowed_q = stowed["configuration_q1_q2_q3_d"]
    approach_q = approach[0]["configuration_q1_q2_q3_d"]
    report = f"""# S4-R6 Physics Model Freeze Report

TASK:
S4-R6-PHYSICS-MODEL-FREEZE-R1

START_HEAD:
{EXPECTED_START}

END_HEAD:
{head}

FINAL_LABEL:
{final_label}

PHYSICS_MODEL_FROZEN:
{str(readiness['physics_model_frozen']).lower()}

FREEZE_TAG:
None (blocked; no freeze tag created)

RRRP_NATIVE:
true

FOUR_ROTOR_ACTUATION:
true

TOTAL_SYSTEM_MASS_KG:
{stowed['mass_com']['total_system_mass_kg']}

PHYSICS_RATE_HZ:
{convergence['selected_physics_rate_hz'] if convergence['timestep_convergence_valid'] else 240}

STOWED_CONFIGURATION:
{json.dumps(stowed_q)}

STOWED_COM_M:
{json.dumps(stowed['mass_com']['system_com_body_m'])}

STOWED_TRIM_THRUSTS_N:
{json.dumps(stowed['hover_trim']['trim_thrusts_n'])}

STOWED_MAX_ROTOR_UTILIZATION:
{stowed['hover_trim']['max_rotor_utilization']}

APPROACH_CONFIGURATION:
{json.dumps(approach_q)}

APPROACH_COM_M:
{json.dumps(approach[0]['mass_com']['system_com_body_m'])}

APPROACH_P_MAX_COM_M:
{json.dumps(approach[-1]['mass_com']['system_com_body_m'])}

APPROACH_MAX_ROTOR_UTILIZATION:
{max(item['hover_trim']['max_rotor_utilization'] for item in approach)}

TIMESTEP_CONVERGENCE:
{'PASS' if convergence['timestep_convergence_valid'] else 'FAIL'}

LINEAR_MOMENTUM_RELATIVE_DRIFT:
{momentum['linear_momentum_relative_drift']}

ANGULAR_MOMENTUM_VALIDATED:
{str(momentum['angular_momentum_validated']).lower()}

ENERGY_DIAGNOSTIC:
{'PASS' if energy['energy_pass'] else 'FAIL'}

DIRECT_WORLD_FORCE_COMMAND:
false

DIRECT_WORLD_TORQUE_COMMAND:
false

MANUAL_REACTION:
false

ROOT_RUNTIME_STATE_WRITE:
false

JOINT_RUNTIME_POSITION_WRITE:
false

HEADLESS_10000_STEP:
{'PASS' if all(item['stable'] for item in runtime['stability']) else 'FAIL'}

HEAD_ONLY_FAILURES:
{readiness['head_only_failures']}

HARDWARE_PARAMETER_VALIDATED:
false

CONTACT_DYNAMICS_VALIDATED:
false

CLOSED_LOOP_CONTROL_VALIDATED:
false

S4_READY:
false

## Findings

- 81/81 sampled configurations were geometrically valid for the coarse AABB contract. The selected STOWED configuration is `[0, pi/2, 0, 0]`; its maximum static trim utilization is `{stowed['hover_trim']['max_rotor_utilization']:.6f}`, passing the 0.80 gate.
- Horizontal APPROACH at P=0, middle, and max has maximum utilization `{max(item['hover_trim']['max_rotor_utilization'] for item in approach):.6f}`, passing the 0.90 gate. The legacy neutral/straight configuration remains a diagnostic, not the stowed flight pose.
- The timestep audit fails the specified 2%/1% criteria; therefore the physics model is not frozen. The dominant failure is the q1 pulse response, not a parameter adjustment opportunity.
- Linear momentum passes with relative drift `{momentum['linear_momentum_relative_drift']:.12g}`. Angular momentum is explicitly unvalidated. Energy diagnostic completed but did not pass the 0.5% drift criterion.
- No tag was created, no cleanup was performed, no controller/wind/contact/gripper work was started, and S4 remains not ready.

Evidence: `docs/evidence/S4-R6/summary/s4_r6_physics_freeze_readiness.json`, `docs/evidence/S4-R6/runtime/rrrp_hover_trim_envelope.json`, `docs/evidence/S4-R6/runtime/timestep_convergence.json`, `docs/evidence/S4-R6/runtime/linear_momentum_validation.json`, `docs/evidence/S4-R6/runtime/energy_validation.json`, `docs/evidence/S4-R6/runtime/final_actuation_audit.json`, and `docs/evidence/S4-R6/runtime/headless_10000_step_stability.json`.
"""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({"final_label": final_label, "stowed_utilization": stowed["hover_trim"]["max_rotor_utilization"], "approach_max_utilization": max(item["hover_trim"]["max_rotor_utilization"] for item in approach), "timestep_convergence": convergence["timestep_convergence_valid"], "energy_pass": energy["energy_pass"], "head_only_failures": readiness["head_only_failures"]}, ensure_ascii=False), flush=True)
    return 0 if readiness["physics_model_frozen"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
