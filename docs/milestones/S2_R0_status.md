# S2-R0 状态：SUBMITTED_FOR_REVIEW

## 结论

`G_ARM_READY_FOR_FULL_PLANNING`。在官方 Delta 几何和本轮明确标注的简化横担标称场景中，P0–P6 七个候选位姿均满足暂定的水平工具轴、关节余量和基本代理 clearance；这只说明“可以进入完整规划设计”，不等于完整 S2 轨迹规划通过。

## 状态门槛

- S2-R0：`SUBMITTED_FOR_REVIEW`
- S2：`IN_PROGRESS`
- S3–S8：`FROZEN`

## 证据

- 官方模型合同：`docs/evidence/S2-R0/robot_model/`
- 坐标系合同：`docs/coordinate_frame_contract.md`
- 场景/模型/门槛配置：`configs/scene/s2_crossarm_nominal.yaml`、`configs/robot/s2_delta_arm.yaml`、`configs/planner/s2_workspace_gate.yaml`
- 100k workspace：`docs/evidence/S2-R0/workspace_sampling_manifest.json`；NPZ 保留本地，不提交大文件
- G-ARM 结果：`docs/evidence/S2-R0/g_arm_preflight.json`
- 报告：`docs/reports/S2-R0_delta_workspace_preflight_report.md`

## 明确限制

横担/障碍/机体/旋翼代理尺寸、工具轴和安全阈值是 `PROVISIONAL_S2_ASSUMPTION`；未运行 AM-Planner 连续全轨迹优化，未进入 G-BRIDGE、Isaac Lab 或 S3。
