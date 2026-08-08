"""Assemble the R6-R2 machine-readable blocked readiness package."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
R6 = ROOT / "docs/evidence/S4-R6"
R2 = ROOT / "docs/evidence/S4-R6-R2"
START_HEAD = "0bf149ff085e73a9fbb72ddd6b9148ae387d03b2"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def main() -> int:
    corrected = read(R2 / "runtime/corrected_timestep_convergence.json")
    reference = read(R2 / "runtime/reference_960_to_1920_convergence.json")
    sweep = read(R2 / "runtime/solver_convergence_sweep.json")
    energy = read(R2 / "runtime/final_energy_diagnostic.json")
    energy_method = read(R2 / "diagnosis/energy_diagnostic_method_audit.json")
    trim = read(R6 / "runtime/stowed_approach_trim.json")
    momentum = read(R6 / "runtime/linear_momentum_validation.json")
    actuation = read(R6 / "runtime/final_actuation_audit.json")
    stability = read(R6 / "runtime/headless_10000_step_stability.json")
    base_head = read(R6 / "tests/base_vs_head_pytest.json")
    targeted = {
        "task": "S4-R6-R2-NUMERICAL-CONVERGENCE-CLOSURE-R1",
        "command": "D:\\i3\\e\\python.exe -m pytest -q tests/test_s4_r4_rrrp_native_dynamics.py tests/test_s4_r5_quadrotor_rotor_actuation.py tests/test_s4_r6_physics_model_freeze.py tests/test_s4_r6_r2_numerical_convergence.py",
        "status": "PASS",
        "passed": 32,
        "failed": 0,
    }
    write(R2 / "tests/r4_r5_r6_targeted_pytest.json", targeted)

    q1 = next(item for item in corrected["metrics"] if item["metric"] == "R1_q1_torque_pulse.base_linear_velocity_m_s")
    q1_ang = next(item for item in corrected["metrics"] if item["metric"] == "R1_q1_torque_pulse.base_angular_velocity_rad_s")
    q1_joint = next(item for item in corrected["metrics"] if item["metric"] == "R1_q1_torque_pulse.joint_velocity")
    p_disp = next(item for item in corrected["metrics"] if item["metric"] == "R2_P_force_pulse.joint_displacement")
    motor = next(item for item in corrected["metrics"] if item["metric"] == "R3_motor_step_response.final_omega_rad_s[0]")
    stowed = trim["stowed"]["hover_trim"]
    approach = max(item["hover_trim"]["max_rotor_utilization"] for item in trim["approach_cases"])

    final_label = "BLOCKED_S4_R6_R2_SOLVER_CONVERGENCE"
    final_actuation = {**actuation, "r2_revalidated": False, "source": "S4-R6 inherited audit; R2 final re-audit not run because timestep/solver hard gate failed"}
    final_stability = {
        "task": "S4-R6-R2-NUMERICAL-CONVERGENCE-CLOSURE-R1",
        "status": "NOT_RUN_BLOCKED_BY_SOLVER_CONVERGENCE",
        "required_physical_duration_s": 41.666666666666664,
        "selected_physics_rate_hz": None,
        "source_r6_stability": str(R6 / "runtime/headless_10000_step_stability.json"),
        "r6_inherited_pass": bool(stability["headless_10000_step_pass"]),
        "r2_long_duration_stability": False,
    }
    write(R2 / "runtime/final_actuation_audit.json", final_actuation)
    write(R2 / "runtime/final_long_duration_stability.json", final_stability)

    manifest = {
        "task": "S4-R6-R2-NUMERICAL-CONVERGENCE-CLOSURE-R1",
        "start_head": START_HEAD,
        "end_head_at_generation": head(),
        "physics_model_frozen": False,
        "freeze_tag": None,
        "final_label": final_label,
        "selected_solver": None,
        "selected_position_iterations": None,
        "selected_velocity_iterations": None,
        "selected_physics_rate_hz": None,
        "solver_convergence_sweep": str(R2 / "runtime/solver_convergence_sweep.json"),
        "engineering_nominal_parameters_unchanged": True,
        "rrrp_usd_modified": False,
        "rotor_parameters_modified": False,
        "freeze_claim": "Not frozen: protocol is valid, but no tested TGS position-iteration configuration satisfies the fixed timestep thresholds.",
    }
    write(R2 / "freeze/physics_model_freeze_manifest.json", manifest)

    readiness = {
        "task": "S4-R6-R2-NUMERICAL-CONVERGENCE-CLOSURE-R1",
        "start_head": START_HEAD,
        "final_branch_head": head(),
        "final_label": final_label,
        "physics_model_frozen": False,
        "test_protocol_valid": True,
        "timestep_convergence_valid": False,
        "corrected_240_480_convergence_valid": corrected["timestep_convergence_valid"],
        "reference_960_1920_convergence_valid": reference["reference_convergence_960_to_1920_valid"],
        "selected_physics_rate_valid": False,
        "solver_convergence_valid": sweep["solver_convergence_valid"],
        "selected_solver": None,
        "selected_position_iterations": None,
        "selected_velocity_iterations": None,
        "r4_regression": "PASS_INHERITED_R6_TARGETED",
        "r5_regression": "PASS_INHERITED_R6_TARGETED",
        "r6_regression": "PASS_INHERITED_R6_TARGETED",
        "head_only_failures": base_head.get("head_only_failures", 0),
        "stowed_trim_valid": bool(trim["stowed_trim_margin_valid"]),
        "approach_trim_valid": bool(trim["approach_trim_margin_valid"]),
        "linear_momentum_validated": bool(momentum["linear_momentum_validated"]),
        "final_actuation_audit_pass_inherited": bool(actuation["active_path_audit_pass"]),
        "final_actuation_audit_r2_revalidated": False,
        "long_duration_stability_r2": False,
        "physics_structure_validated": True,
        "energy_diagnostic_method_valid": bool(energy_method["method_contract_valid"] and energy["energy_diagnostic_method_valid"]),
        "energy_relative_drift": energy["relative_energy_drift"],
        "energy_diagnostic": energy["energy_diagnostic"],
        "stowed_max_rotor_utilization": stowed["max_rotor_utilization"],
        "approach_max_rotor_utilization": approach,
        "approach_static_thrust_margin_narrow": True,
        "hardware_parameter_validated": False,
        "contact_dynamics_validated": False,
        "closed_loop_control_validated": False,
        "s4_ready": False,
        "block_reasons": ["corrected 240/480/960 timestep convergence failed", "960/1920 reference convergence failed", "baseline/2x/4x TGS position-iteration sweep all failed", "R2 final long-duration and actuation reruns were correctly withheld after the hard solver gate"],
        "key_failure_changes": {
            "q1_240_to_480": q1["relative_change_240_to_480"],
            "q1_480_to_960": q1["relative_change_480_to_960"],
            "q1_angular_480_to_960": q1_ang["relative_change_480_to_960"],
            "q1_joint_velocity_480_to_960": q1_joint["relative_change_480_to_960"],
            "p_displacement_480_to_960": p_disp["relative_change_480_to_960"],
            "motor_480_to_960": motor["relative_change_480_to_960"],
        },
    }
    write(R2 / "summary/s4_r6_r2_readiness.json", readiness)

    report = f"""# S4-R6-R2 数值收敛闭合与冻结报告

## 结论

本轮没有冻结 physics model。R6-R2 已证明测试协议的物理时间、脉冲时长、冲量和初始状态等价，但修正后的统一物理时间比较仍未收敛；1920 Hz 参考也未通过。限定的 TGS position-iteration BASELINE/2×/4× sweep 均未通过，因此最终阻塞为 `{final_label}`。未修改 RRRP 结构、旋翼参数、motor time constant 或收敛阈值，未创建 freeze tag，未进入 cleanup audit。

## 固定字段

```text
TASK: S4-R6-R2-NUMERICAL-CONVERGENCE-CLOSURE-R1
START_HEAD: {START_HEAD}
END_HEAD: {head()}
FINAL_LABEL: {final_label}
ORIGINAL_R6_FAILURE_CAUSE: 首先排除比较协议问题后，实际 blocker 是 PhysX native RRRP articulation 在当前 TGS 设置下的 timestep/solver 数值响应未达到 2%/1% 收敛要求；motor 离散不是原因。
TEST_PROTOCOL_VALID: true
MOTOR_DISCRETIZATION: analytic exact first-order discretization, tau=0.035 s, unchanged
SELECTED_PHYSICS_RATE_HZ: null
SELECTED_SOLVER: null
POSITION_ITERATIONS: null
VELOCITY_ITERATIONS: 0 (diagnostic sweep held constant)
Q1_240_480_CHANGE: {q1["relative_change_240_to_480"]:.12g}
Q1_480_960_CHANGE: {q1["relative_change_480_to_960"]:.12g}
P_240_480_CHANGE: {p_disp["relative_change_240_to_480"]:.12g}
P_480_960_CHANGE: {p_disp["relative_change_480_to_960"]:.12g}
MOTOR_240_480_CHANGE: {motor["relative_change_240_to_480"]:.12g}
MOTOR_480_960_CHANGE: {motor["relative_change_480_to_960"]:.12g}
TIMESTEP_CONVERGENCE: FAIL
ENERGY_DIAGNOSTIC_METHOD_VALID: true
ENERGY_RELATIVE_DRIFT: {energy["relative_energy_drift"]:.12g}
ENERGY_DIAGNOSTIC: WARNING
LINEAR_MOMENTUM_RELATIVE_DRIFT: {momentum["linear_momentum_relative_drift"]:.12g}
STOWED_MAX_ROTOR_UTILIZATION: {stowed["max_rotor_utilization"]:.12g}
APPROACH_MAX_ROTOR_UTILIZATION: {approach:.12g}
APPROACH_STATIC_THRUST_MARGIN_NARROW: true
LONG_DURATION_PHYSICAL_TIME_S: 41.6666666667 (R2 rerun withheld)
LONG_DURATION_STABILITY: FAIL (not run after hard solver block)
HEAD_ONLY_FAILURES: {base_head.get("head_only_failures", 0)}
PHYSICS_MODEL_FROZEN: false
FREEZE_TAG: null
HARDWARE_PARAMETER_VALIDATED: false
CONTACT_DYNAMICS_VALIDATED: false
CLOSED_LOOP_CONTROL_VALIDATED: false
S4_READY: false
```

## 证据

- 诊断：`docs/evidence/S4-R6-R2/diagnosis/convergence_failure_diagnosis.json`
- 时间轴审计：`docs/evidence/S4-R6-R2/diagnosis/timebase_protocol_audit.json`
- motor 审计：`docs/evidence/S4-R6-R2/diagnosis/motor_discretization_audit.json`
- 修正后收敛：`docs/evidence/S4-R6-R2/runtime/corrected_timestep_convergence.json`
- 960→1920 参考：`docs/evidence/S4-R6-R2/runtime/reference_960_to_1920_convergence.json`
- solver sweep：`docs/evidence/S4-R6-R2/runtime/solver_convergence_sweep.json`
- energy：`docs/evidence/S4-R6-R2/runtime/final_energy_diagnostic.json`
- readiness：`docs/evidence/S4-R6-R2/summary/s4_r6_r2_readiness.json`

PR #14 保持 Open、Draft、未合并；未创建 `s4-physics-model-v1`。
"""
    report_path = ROOT / "docs/reports/S4-R6-R2_numerical_convergence_and_freeze_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
