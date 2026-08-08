# S4-R6-R2 数值收敛闭合与冻结报告

## 结论

本轮没有冻结 physics model。R6-R2 已证明测试协议的物理时间、脉冲时长、冲量和初始状态等价，但修正后的统一物理时间比较仍未收敛；1920 Hz 参考也未通过。限定的 TGS position-iteration BASELINE/2×/4× sweep 均未通过，因此最终阻塞为 `BLOCKED_S4_R6_R2_SOLVER_CONVERGENCE`。未修改 RRRP 结构、旋翼参数、motor time constant 或收敛阈值，未创建 freeze tag，未进入 cleanup audit。

## 固定字段

```text
TASK: S4-R6-R2-NUMERICAL-CONVERGENCE-CLOSURE-R1
START_HEAD: 0bf149ff085e73a9fbb72ddd6b9148ae387d03b2
END_HEAD: 0bf149ff085e73a9fbb72ddd6b9148ae387d03b2
FINAL_LABEL: BLOCKED_S4_R6_R2_SOLVER_CONVERGENCE
ORIGINAL_R6_FAILURE_CAUSE: 首先排除比较协议问题后，实际 blocker 是 PhysX native RRRP articulation 在当前 TGS 设置下的 timestep/solver 数值响应未达到 2%/1% 收敛要求；motor 离散不是原因。
TEST_PROTOCOL_VALID: true
MOTOR_DISCRETIZATION: analytic exact first-order discretization, tau=0.035 s, unchanged
SELECTED_PHYSICS_RATE_HZ: null
SELECTED_SOLVER: null
POSITION_ITERATIONS: null
VELOCITY_ITERATIONS: 0 (diagnostic sweep held constant)
Q1_240_480_CHANGE: 0.200608985854
Q1_480_960_CHANGE: 0.0908673312036
P_240_480_CHANGE: 0.0055565925751
P_480_960_CHANGE: 0.00275663266853
MOTOR_240_480_CHANGE: 0
MOTOR_480_960_CHANGE: 0
TIMESTEP_CONVERGENCE: FAIL
ENERGY_DIAGNOSTIC_METHOD_VALID: true
ENERGY_RELATIVE_DRIFT: 4665.3998113
ENERGY_DIAGNOSTIC: WARNING
LINEAR_MOMENTUM_RELATIVE_DRIFT: 2.642050709e-07
STOWED_MAX_ROTOR_UTILIZATION: 0.729019827163
APPROACH_MAX_ROTOR_UTILIZATION: 0.898147798764
APPROACH_STATIC_THRUST_MARGIN_NARROW: true
LONG_DURATION_PHYSICAL_TIME_S: 41.6666666667 (R2 rerun withheld)
LONG_DURATION_STABILITY: FAIL (not run after hard solver block)
HEAD_ONLY_FAILURES: 0
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
