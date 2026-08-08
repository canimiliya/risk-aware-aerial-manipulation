# S4-R5 quadrotor rotor actuation report

## 结论

本轮在不修改 R4 RRRP USD 的前提下，建立了由四个局部 body-frame rotor actuator 驱动的浮动四旋翼基座。四个 rotor 的力、作用点、旋向、`k_f/k_m`、转速上下限和一阶电机时间常数均来自 `configs/s4/rrrp_quadrotor_design.yaml`。R5 通过，但这不是硬件标定、闭环控制或 S4 总体验收。

## 已验证

- RRRP 保持 4 DOF（3R+1P）、0.63 kg、0.47 m 最大几何 reach 和 0.08 m P 行程。
- 从 PhysX 刚体质量与位姿 readback 汇总整机质量：1.65 kg；中性构型系统 COM（body frame）：`[0.0923939299, 0, 0] m`。
- X 构型 4×4 allocation matrix 由 rotor position/axis/spin 自动生成，`rank=4`。
- 静态中性构型 hover trim：`[6.4500397166, 6.4500397166, 1.6432102761, 1.6432102761] N`；力残差为 0，力矩残差约 `2.49e-16 N*m`，全部非负且低于单 rotor 最大推力。
- collective、roll、pitch、yaw 的符号测试均 PASS；单 rotor pulse 记录了四个 rotor 的速度、推力、反扭矩、局部作用点和基座 readback。
- 电机一步响应按 `tau=0.035 s` 的一阶离散模型运行，不存在瞬时满速；实际转速和推力均受 min/max 饱和约束。
- rotor thrust 通过 `apply_forces_and_torques_at_pos(..., positions=position_body, is_global=False)` 施加；没有 active direct world-force/world-torque 命令。
- 关闭 rotor 后，q1 effort 和 P effort 仍能产生 RRRP 运动及浮动基座自然响应；没有 controller 抹平反作用。
- 四组 5000-step headless case 均 NaN=0、Inf=0、native exit=false、physics explosion=false。

## 物理边界

R5 是 point-thrust rotor model，含 motor dynamics 和 rotor reaction torque；不含桨叶刚体、尾流、地面效应、空气动力干扰或真实推力台参数。重力开启且没有姿态控制器时，固定 trim 下的自由飞行位移会增长；该开放环漂移被保留为边界记录，不被宣称为 hover control。

`HARDWARE_PARAMETER_VALIDATED=false`、`WIND_MODEL_VALIDATED=false`、`CONTACT_DYNAMICS_VALIDATED=false`、`CLOSED_LOOP_CONTROL_VALIDATED=false`、`S4_READY=false`。

## 范围

本轮未修改 Delta 权威 USD、R2 视觉/视频、R4 正式证据、机械臂结构或参数；未进入风、接触、控制、安装、R6。既有未跟踪历史输出保留。

## 最终格式

```text
TASK:
S4-R5-QUADROTOR-ROTOR-ACTUATION-R1

START_HEAD:
e24da8bc2ccbc5a37ac84572a080d067a4d5ac5a

END_HEAD:
419157864308890bfa5121b0c5c67b7179bb2d17

FINAL_LABEL:
S4_R5_QUADROTOR_ROTOR_ACTUATION_READY

ACTIVE_MANIPULATOR:
RRRP

ROTOR_COUNT:
4

TOTAL_SYSTEM_MASS_KG:
1.6499999985

SYSTEM_COM_NEUTRAL_M:
[0.0923939299,0.0,0.0]

ROTOR_CONFIGURATION:
X

ROTOR_ARM_RADIUS_M:
0.22

MAX_THRUST_PER_ROTOR_N:
7.35

THRUST_TO_WEIGHT_MAX:
1.8158

MOTOR_TIME_CONSTANT_S:
0.035

ALLOCATION_MATRIX_RANK:
4

HOVER_TRIM_THRUSTS_N:
[6.4500397166,6.4500397166,1.6432102761,1.6432102761]

HOVER_TRIM_FORCE_RESIDUAL_N:
0.0

HOVER_TRIM_TORQUE_RESIDUAL_NM:
2.486410087150353e-16

COLLECTIVE_SIGN:
PASS

ROLL_SIGN:
PASS

PITCH_SIGN:
PASS

YAW_SIGN:
PASS

DIRECT_WORLD_FORCE_COMMAND:
false

DIRECT_WORLD_TORQUE_COMMAND:
false

MOTOR_DYNAMICS:
true

ROTOR_SATURATION:
true

RRRP_NATIVE:
true

MANUAL_REACTION_DISABLED:
true

HEADLESS_5000_STEP:
PASS

HEAD_ONLY_FAILURES:
0

HARDWARE_PARAMETER_VALIDATED:
false

CLOSED_LOOP_CONTROL_VALIDATED:
false

S4_READY:
false
```

1. 四旋翼执行器是否已经真实接入？是，四个 rotor 已以局部点推力和反扭矩接入 floating PhysX base。
2. 当前整机还缺什么？硬件参数标定、风/接触模型、闭环控制和 S4 总体验收。
3. 是否可以进入动力学冻结 R6？可以提交 R5 结果等待高级总控复核；本代理不执行 R6。
