# S2-R1 最终审查：连续运动学预规划

## Decision

`PASS_WITH_LIMITATIONS`

本次审查确认 S2-R1 的证据可以复核，但证据范围必须限定为 fixed-WB continuous kinematic preplanning（固定 W→B 的连续运动学预规划）。它不是 AM-Planner 连续优化、动态车辆轨迹或 ROS PolynomialTrajectory。

## Reproducible evidence

- P0–P6：7 个审计航点，段内 quintic C2 插值。
- 601 个采样点：无效点 0。
- 最小标称代理 clearance：0.0162705391 m。
- 最小归一化关节余量：0.4044585987。
- 最小 Jacobian 奇异值：0.0211343153。
- 最大 Jacobian 条件数：3.8633689778。
- 官方 AM-Planner 来源 commit：`7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`；官方源码与几何未修改。

## Accepted limitations

1. `vehicle_pose_WB` 全部为 `[0, 0, 0, 0, 0, 0]`，只是固定参考，不是动态 W→B。
2. 车辆动力学、风场、质量惯量、飞控闭环尚未纳入。
3. 工具长度和完整 6D 姿态未知；`[1, 0, 0]` 只代表暂定水平工具轴。
4. 机体、旋翼、横担和工具使用代理几何，不是 mesh 精确碰撞。
5. 未启动 `se3_node`，未执行 JPS/MINCO、`/trajectory`、`/trajectory_arm`，不能宣称真实 AM-Planner 规划。
6. S2 仍为 `IN_PROGRESS`，S3–S8 仍为 `FROZEN`。

## Status contract

- S2-R0：`PASS_WITH_LIMITATIONS`。
- S2-R1：`PASS_WITH_LIMITATIONS`。
- S2：`IN_PROGRESS`。
- S3–S8：`FROZEN`。
