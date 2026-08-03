# S1 最终审查（2026-08-03）

## 结论

`S1-R2：PASS`；`S1：PASS_WITH_LIMITATIONS`。S1 已完成 AM-Planner 固定源码的受控复现、四组官方任务运行、真实 `PolynomialTrajectory` 导出合同、waypoint 变体和重复性证据。限制是 Catkin 上游 warning、nvidia-smi 进程名显示限制和成功后非致命的 `No logs to publish!`，三项均保留原始证据并被分类为非阻断。

## 审查范围

- 固定 AM-Planner commit：`7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。
- S1-R1：四次 GPU 双轨迹运行，ABI 检查无 Python 3.8/runtime-not-found，最终 `PASS_WITH_LIMITATIONS`。
- S1-R2：write 19 段、grasp 4 段、lift 3 段、grasp repeat 4 段；100 Hz 采样、NaN/Inf、CSV/NPZ、一致性和连续性验证通过。
- waypoint：独立 overlay 将 `object_px` 从 `0.00` 改为 `0.05`，成功 capture，历史两次失败尝试保留。
- 可视化：4 个 GIF 由 manifest 锁定，4 个 PNG 均小于 2 MB。
- 全局 S0 audit：exit=0；Windows symlink/junction 被安全跳过并记录 `skipped_paths`，未静默吞错。

## Git 事实

- S1-R2 实现提交：`8d9d1da`。
- 视频 manifest 提交：`0fbbbe4`。
- PR #4 原始 S1-R2 Head：`f12f61ab1925e30dfa31dbb4c8a2f63c023cfb0a`；A 阶段最终审阅提交：`e66c4783d5c80492bb0099c35f144d5eeac06df5`。
- S1-R1 合并后的 main 基线：`a028f265c616be922e5ab0ccff907fcbeda06273`。

## 证据

- `docs/evidence/S1/final_acceptance/s1_final_acceptance.json`
- `docs/evidence/S1-R1/final_acceptance/s1_r1_final_acceptance.json`
- `docs/evidence/S1-R2/final_acceptance/s1_r2_trajectory_export_audit.json`
- `docs/reviews/S1-R1_warning_acceptance_review_2026-08-03.md`
- `docs/trajectory_contract.md`

## 门槛边界

本审查不代表完整 S2 通过，不运行 IL/Polynomial_DiT，不修改 AM-Planner `.cpp/.h`，不修改系统 ROS，不修改既有轨迹原始数值。下一项仅允许在 S2-R0 Draft PR 中提交官方模型/场景合同和几何工作空间预检。
