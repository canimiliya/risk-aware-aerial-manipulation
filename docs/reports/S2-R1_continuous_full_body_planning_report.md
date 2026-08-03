# S2-R1 连续运动学预规划最终审查报告（2026-08-03）

Terminology note:
本文件名中的 `continuous_full_body_planning` 为历史名称；实际证据范围是 fixed-WB continuous kinematic preplanning，不是 AM-Planner optimization。

## 结论

本轮把 S2-R0 的 P0–P6 静态候选扩展为一条可复现的连续运动学预规划轨迹。状态记录同时携带车辆 `W→B` 六维固定参考位姿和 Delta 机械臂三关节；由于官方资料没有真实车辆动态状态，本轮将 `W→B` 明确固定为零参考位姿并标注 `FIXED_WB_REFERENCE_PROVISIONAL`。

审计判定：`PASS_WITH_LIMITATIONS`。

## 方法与证据

- 官方来源仍固定在 AM-Planner `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`，没有修改 `third_party/am-planner` 或官方算法源码。
- P0–P6 使用既有候选关节序列，段内采用五次 C2 混合，端点速度和加速度为零；每段 101 点，总计 601 点。该轨迹是 seed/reference，不是 AM-Planner 输出。
- 每个点复用官方 Delta FK，检查 FK 有限性、官方关节限位、暂定水平工具轴、上/下臂到障碍代理的 clearance，以及机体/旋翼半径代理。
- Jacobian 仍是官方位置 FK 的中心有限差分，只用于运动学诊断，不是飞行器—机械臂动力学 Jacobian。

| 指标 | 结果 | 暂定门槛 |
|---|---:|---:|
| 连续采样点 | 601 | 601 |
| 无效采样点 | 0 | 0 |
| 最小标称代理 clearance | 0.01627 m | ≥ 0.010 m |
| 最小关节归一化余量 | 0.40446 | ≥ 0.10 |
| 最小 Jacobian 奇异值 | 0.02113 | > 0 |
| 最大 Jacobian 条件数 | 3.86337 | < 100 |

## R0 最终收口

S2-R0 的官方模型合同、100k 工作空间、宽松/标称/狭窄敏感性和 G-ARM 预检均已保留。R0 的最终含义是 `PASS_WITH_LIMITATIONS`：静态预检门槛通过，但横担、障碍、机体、旋翼和工具参数仍是暂定代理；这不是完整 S2 规划通过。

## Accepted limitations

- `W→B` 固定为零参考，尚无真实动态车辆轨迹、车辆动力学或飞控约束。
- 工具长度与完整 6D 工具姿态未知；`[1,0,0]` 仅为暂定水平工具轴。
- 碰撞检查使用暂定球体/AABB/代理几何，不是 mesh 精确碰撞。
- 未启动 `se3_node`，未运行 JPS/MINCO、`/trajectory` 或 `/trajectory_arm`，因此不构成真实 AM-Planner 证据。
- S2-R1 不是完整 S2 验收，S3–S8 保持冻结。

## 需要人工确认的项目

下一次收口前需要确认真实 `W→B` 轨迹、工具/夹具姿态与尺寸、横担/导线/绝缘子几何、mesh 碰撞、动力学限制和规划器输入合同。确认前，S2 保持 `IN_PROGRESS`，S3–S8 保持 `FROZEN`。
