# S3-R0 离线轨迹协议 v1

本协议把 S2-R6 冻结的 `nominal_100w0` 与 `nominal_repeat_final_100w0` 原始多项式转换为可重复的 reference-state playback 输入。协议不改写 S2 轨迹、barrier、anchor、权重、tau、100w0 或 0.010 m gate。

bundle 保存原始 base/arm polynomial、200 Hz canonical full-state、阶段标注和 SHA-256 manifest。200 Hz 只是 canonical 交换格式；Isaac playback 必须直接从 raw polynomial 在 240 Hz 物理时间上求值，不能把 200 Hz 帧逐帧当作 PhysX step。

## 姿态和单位

所有量使用 SI 单位：时间秒、位置米、速度米/秒、加速度米/秒²、jerk 米/秒³、关节角弧度。`base_quaternion_WB_wxyz` 明确使用 Isaac/USD 常用的 `[w, x, y, z]` 顺序；不得与 `[x, y, z, w]` 混用。姿态和 `base_body_omega_B_rad_s` 由项目已有 `playback_validator.validate_attitude` 复用 `OfficialFlatnessMap` 重建，来源标记为 `S2_OFFICIAL_FLATNESS_MAP_RECONSTRUCTION`，同时保存正 thrust。

姿态输入沿用 S2 回放合同：源 `start_yaw/final_yaw` 的线性偏航约定，以及恒定 `yaw_dot=0.01 rad/s`。这不是重新设计 yaw/yaw_dot，也不是闭环飞控姿态输出。

## B→A0 与世界系 EE

`T_B_A0` 直接复用 `planner_bridge.execution.full_body_proxy.T_B_A0`。独立世界系 EE 公式为：

```text
p_WE = p_WB + R_WB @ (R_BA0 @ p_A0E + t_BA0)
```

因此禁止使用 `p_WB + p_A0E`。工具方向只保存等效水平约束的方向向量，不虚构完整末端 quaternion：

```text
direction_W = R_WB @ R_BA0 @ direction_A0
```

旧 identity quaternion/zero-omega bundle 的 SHA 和 validator 拒绝结果保存在 `docs/evidence/S3-R0/protocol_v1_frame_correction.json`。

## Playback 边界

S3 允许 `S3_KINEMATIC_PLAYBACK_ARTICULATION`：通过导入 USD 的 active joint state 进行离线 reference playback、官方 FK、read-back 和场景距离检查。它不等同于完整闭链动力学；`full_closed_chain_dynamics=false`，S4 前仍需单独解决动力学 articulation 或经批准的 surrogate。

导出命令：

```powershell
$env:PYTHONPATH = (Get-Location).Path
python planner_bridge/protocol/export_s3_trajectory.py
```

Isaac 阶段只读取离线 bundle 和 raw polynomial，不建立 ROS/ROS2 bridge。
