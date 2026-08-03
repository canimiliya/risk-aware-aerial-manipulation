# S2-R2 AM-Planner 横担连续规划报告

## 结论

本轮完成了合同纠正、固定官方源复核、真实 ROS/GPU AM-Planner 运行、双轨迹捕获、100/200/400 Hz 导出和独立连续验证。当前标签为 `SUBMITTED_S2_R2_AM_PLANNER_READY`，状态是提交复核，不是 S2 总体 PASS。

旧的 `BLOCKED_S2_R2_PLANNER_CONTRACT` 已保留为历史记录，并改标为 `REVISED_S2_R2_PLANNER_CONTRACT`：旧判断把“优化器内部 Cartesian arm 变量”错误地当成“任务必须显式提供 Delta q[3]”。

## 真实运行结果

| 场景 | ROS 双轨迹 | base 100 Hz 路径长度 | arm Cartesian 100 Hz 路径长度 | base proxy 最小 clearance | 世界系末端 proxy 最小 clearance | 结果 |
|---|---|---:|---:|---:|---:|---|
| smoke_free | `/trajectory` + `/trajectory_arm` | 5.7289 m | 0.8692 m | 0.1833 m | 0.0585 m | PASS |
| loose | `/trajectory` + `/trajectory_arm` | 6.0367 m | 0.9357 m | 0.0243 m | 0.0510 m | PASS |
| nominal | `/trajectory` + `/trajectory_arm` | 7.5745 m | 0.8692 m | 0.0515 m | 0.0332 m | PASS |
| nominal repeat | `/trajectory` + `/trajectory_arm` | 7.5745 m | 0.8692 m | 0.0515 m | 0.0332 m | PASS |
| narrow diagnostic | `/trajectory` + `/trajectory_arm` | 6.1802 m | 0.9357 m | 0.0166 m | 0.0250 m | PASS，边界诊断 |

nominal 最危险项是 `end_effector_world_proxy`，100 Hz 时刻 `5.41 s`，最近地图点 `[-0.08, 0.18, 0.56] m`，最小值 `0.0332307 m`，高于 `0.010 m` gate。独立重采样的 100/200/400 Hz 结果均为有限值；nominal/repeat 的合同、base/arm/end-effector 起终点和 gate clearance 差异均为 0。

## 合同与来源

- 官方 AM-Planner commit：`7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。
- 选定源 clone：`/home/amplanner/am-planner-ws/src/am-planner`；tracked SHA manifest：`0518ef370e84a7d6a7fad4924f080616ea2753170c2a0ce380d8664d1492d528`。
- 新工作区：`/home/amplanner/am-planner-s2-r2-ws/src/am-planner`；官方 commit 前为 clean，仅接受两个 S1 ABI CMake patch 后修改两个包 CMakeLists。
- `inter_info` 合同为 `4/7/17/20`；不添加 q[3]。base 是 `3×3` position/velocity/acceleration；arm 是内部 `MINCO_S3_ARM` Cartesian polynomial。
- `/trajectory` 和 `/trajectory_arm` 均为 `quadrotor_msgs/PolynomialTrajectory`；后者不是关节角消息。

## 地图与方向

项目地图发布到 `/global_map`，frame 为 `world`，点云和 SHA manifest 见 `docs/evidence/S2-R2/maps/`。场景生成保留主横担、立柱、邻近障碍和目标代理，没有通过删障碍制造成功。

官方 JPS 日志中 7 段搜索端点与任务 mode-2 轴语义重建结果完全一致：端点误差最大 `0 m`，水平段方向误差最大 `0 deg`，状态为 `EQUIVALENT_HORIZONTAL_DIRECTION_CONSTRAINT`。PolynomialTrajectory 本身不携带原始 mode-2 flag/vector，因此不虚构连续工具轴误差。

## 连续验证边界

- 末端世界轨迹按 `p_WE = p_WB + R_WB p_A0E` 重建；本次消息只有 yaw 边界且为 0，故采用 `R_WB=I` 的可证实特例。
- 官方 `DeltaDisplay::endCallback` 已提供逐点 `IK_kin(x, y, z, theta_vector)`，并把 Cartesian end-effector 点转换为 joint state 后调用 `getJointPoints`；S2-R2 尚未把该官方 IK 应用于整条规划轨迹，因此本报告不宣称连续 joint limits 或全身执行层碰撞闭环。
- yaw=0 只固定偏航；动态 roll/pitch 应由官方 `FlatnessMap` 根据 position/velocity/acceleration/jerk 重建。本轮尚未重建动态 `R_WB(t)`，所以现有 `R_WB=I` 结果仅是 planner-level provisional validation。
- 已 gate 的组件：base body sphere proxy `0.08 m`、重建世界系末端 proxy `0.025 m`。其中 `0.08 m` 来自 Delta static/platform geometry，不自动等于无人机机体半径；S2-R0 的 body/rotor `0.20/0.25 m` 仍标记为 `PROVISIONAL_S2_ASSUMPTION`。
- rotor disk 仅按 S2-R0 暂定尺寸做 diagnostic，不纳入 S2-R2 gate；连杆连续碰撞和 joint-limit 需要官方时间参数化 IK/完整几何执行层，本轮不宣称完成。
- 因此 `0.0332307 m` 只能称为 `S2-R2 planner-level gated proxy clearance`，不是全身碰撞结论，也不是 mesh 精确碰撞。
- clearance threshold sensitivity：nominal 在 `0.02 m` 通过，在 `0.05 m` 和 `0.10 m` 不通过；这是敏感性结果，不是修改 gate。

## 后续边界

S2 继续保持 `IN_PROGRESS`，S3-S8 保持 `FROZEN`。项目负责人需要复核本轮 S2-R2 提交，随后另行决定 S2 最终收口；本轮没有启动后续阶段。
