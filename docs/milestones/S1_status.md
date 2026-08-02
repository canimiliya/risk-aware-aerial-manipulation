# S1 状态：PASS_WITH_LIMITATIONS

## 当前状态

- S1-R1：`PASS_WITH_LIMITATIONS`
- S1-R2：`PASS`
- S1：`PASS_WITH_LIMITATIONS`
- S2：`IN_PROGRESS`（仅 S2-R0 工作空间预检）
- S3–S8：`FROZEN`

## 人话结论

S1 的官方 AM-Planner 复现和轨迹导出验收已经收口，可以进入 S2-R0 的受限预检；仍不能把 S2-R0 的几何预检写成完整 S2 规划通过。

## 接受限制

1. Catkin 上游/ROS-CMake warning：`NON_BLOCKING_UPSTREAM`。
2. `nvidia-smi` 进程名显示 `[Not Found]`：`NON_BLOCKING_ENVIRONMENT`。
3. `[MANAGE]: No logs to publish!` 出现在优化完成和轨迹发布附近：`NON_BLOCKING_POST_SUCCESS`。

## 关键审计

- 最终审计：`docs/evidence/S1/final_acceptance/s1_final_acceptance.json`。
- 全局 S0 审计：`python scripts/audit/check_s0_structure.py`，exit=0。
- S1-R2 审计：errors=0、warnings=0。
- AM-Planner 官方来源和许可证边界保持不变。
