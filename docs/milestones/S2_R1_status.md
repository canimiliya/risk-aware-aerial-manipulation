# S2-R1 状态：SUBMITTED_FOR_REVIEW

## 结论

已完成 P0–P6 的连续全身状态预规划合同：车辆 `W→B` 使用显式固定参考位姿，Delta 臂使用官方闭链 FK，轨迹采用 C2 五次混合并对 601 个连续采样点做有限性、关节余量、工具轴、代理 clearance 和有限差分 Jacobian 审计。

审计结果为 `SUBMITTED_S2_R1_CONTINUOUS_PREPLANNING`。标称暂定场景下连续采样无无效点，最小代理 clearance 为 0.01627 m，最小关节归一化余量为 0.40446，Jacobian 最小奇异值为 0.02113，最大条件数为 3.86337。

## 门槛边界

- S2-R0：`PASS_WITH_LIMITATIONS`（静态工作空间/场景预检已收口，保留暂定几何限制）。
- S2-R1：`SUBMITTED_FOR_REVIEW`（连续位置/运动学预规划已提交）。
- S2：`IN_PROGRESS`；S3–S8：`FROZEN`。

## 尚未完成

- 未获得真实 `W→B` 动态位姿、工具长度/姿态、机体与旋翼 mesh、质量惯量、风场和动力学约束。
- 未运行完整 AM-Planner 连续优化、G-BRIDGE、Isaac/PhysX 或飞行控制闭环。
- 因此不能把本结果写成完整 S2 PASS，也不能推进 S3。

## 证据

- 轨迹：`docs/evidence/S2-R1/continuous_full_body_plan.json`
- 清单：`docs/evidence/S2-R1/continuous_planning_manifest.json`
- 审计：`docs/evidence/S2-R1/final_acceptance/s2_r1_continuous_planning_audit.json`
- 图：`outputs/figures/S2-R1/continuous_full_body_plan.png`
