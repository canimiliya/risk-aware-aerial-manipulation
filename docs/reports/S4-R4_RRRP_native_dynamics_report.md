# S4-R4 RRRP native dynamics report

## 结论

R3 的 Delta 权威 USD 不再修复。本轮建立了独立 RRRP 开链物理资产，并完成 PhysX articulation 的固定基座、浮动基座、effort pulse、solver readback、动量和 P 行程验证。R4 通过，但这不是硬件校准完成，也不是 S4 总体验收，更不是 R5 授权。

## 唯一事实源与资产

- `robot_assets/rrrp/rrrp_design.yaml`：唯一设计参数源；`ENGINEERING_NOMINAL`、`provisional=true`。
- `rrrp_arm.urdf`：由 YAML 生成。
- `rrrp_arm.usd`：独立 USD Physics/PhysX 资产，含固定基座和浮动基座两套 4-DOF articulation。
- 质量与惯量来自同一盒体几何和质量参数；所有正质量刚体和惯量三角不等式通过。
- 浮动 UAV 使用 0.98 kg 与 `[0.018,0.018,0.032]` 的 `PROVISIONAL_LEGACY` 惯性来源；`HARDWARE_PARAMETER_VALIDATED=false`。

## 运行时结果

- fixed base：2000 physics steps，PASS。
- floating base：2000 physics steps，PASS。
- q1/q2/q3/P：仅通过 `ArticulationAction(joint_efforts=...)` 输入；状态由 PhysX readback 获得。
- Python arm integrator、manual reaction、manual arm gravity、reset 后 root/joint pose/velocity 写入：均为 false。
- floating base 在 q1 与 P effort pulse 下均发生自然位姿响应；代码没有人工 reaction call。
- P=0、middle、max 三个 reset-only default/readback case 均在行程内；接触动力学仍未验证。
- 零重力、零外力、逐刚体线速度/质量审计的最大相对线动量漂移：`2.2777646545515437e-06`。

## 回归与边界

定向 R4 合同测试：9 passed。以 R3 起点做 base/head 全套回归：base 84 passed/13 failed，head 93 passed/13 failed，head-only failures=0；13 个失败均为既有 S0/S1/S2/S3 冻结证据或缺失本地轨迹问题。

本轮未修改 Delta 权威 USD，未修 R2 viewport，未生成截图/视频，未做转子、悬停控制、风、接触、抓取、完整轨迹、RL 或 S5。

## 最终格式

```text
TASK:
S4-R4-RRRP-NATIVE-DYNAMICS-R1

START_HEAD:
ee3b3bcae004ecbcc537125654d45752c4d85454

END_HEAD:
2f6c6ca0c9a2d2e9acc104ca3bd359a476b0e63b

FINAL_LABEL:
S4_R4_RRRP_NATIVE_DYNAMICS_READY

ACTIVE_MANIPULATOR:
RRRP

DOF:
4

REVOLUTE_DOF:
3

PRISMATIC_DOF:
1

TOTAL_ARM_MASS_KG:
0.63

MAX_GEOMETRIC_REACH_M:
0.47

P_STROKE_M:
0.08

ARTICULATION_PRESENT:
true

ALL_LINK_INERTIA_VALID:
true

PYTHON_ARM_INTEGRATOR_DISABLED:
true

MANUAL_REACTION_DISABLED:
true

PHYSX_READBACK:
true

FIXED_BASE_2000_STEP:
PASS

FLOATING_BASE_2000_STEP:
PASS

BASE_RESPONSE_Q1:
true

BASE_RESPONSE_P:
true

LINEAR_MOMENTUM_RELATIVE_DRIFT:
2.2777646545515437e-06

ROOT_RUNTIME_STATE_WRITE:
false

JOINT_RUNTIME_POSITION_WRITE:
false

JOINT_RUNTIME_VELOCITY_WRITE:
false

HEAD_ONLY_FAILURES:
0

FULL_ROTOR_ACTUATION:
false

HARDWARE_PARAMETER_VALIDATED:
false

CONTACT_DYNAMICS_VALIDATED:
false

S4_READY:
false
```

## 现在真正解决了什么？

解决了：独立 RRRP 物理资产、PhysX 原生 4-DOF articulation、effort-only 输入、solver readback、浮动基座耦合、P 行程验证和运行时防作弊证据。

## 还有什么？

还缺：硬件 CAD/参数校准、四旋翼真实 rotor actuation、风/接触/摩擦、控制闭环和 S4 总体验收。Delta 旧资产只作为废弃路线证据保留。

## 能不能进入 R5？

不能。本轮只完成 R4；`S4_READY=false`，需要高级总控独立复核并明确下一轮授权后，才能执行 R5。
