# S1-R2 轨迹导出与 waypoint 验收报告（2026-08-03）

## 项目进度

- 开始时总体百分比：仓库没有可审计的统一百分比字段，本轮不虚构百分比；开始状态为 S1-R1 `PASS_WITH_LIMITATIONS`、S1 `IN_PROGRESS`。
- 结束时总体百分比：同上；结束状态为 S1-R2 `SUBMITTED_FOR_REVIEW`、S1 `IN_PROGRESS`。
- S1 完成度：S1-R1 与 S1-R2 已提交审阅；S1 未完成，S2–S8 冻结。

## 结论

S1-R2 已完成并提交审阅。真实消息合同、四组官方轨迹、waypoint 变体、采样/连续性、CSV/NPZ 一致性和四组可视化均有证据；S1 不宣布 PASS。

## A：S1-R1 最终收口

- 三项告警分类：Catkin=`NON_BLOCKING_UPSTREAM`；nvidia-smi `[Not Found]`=`NON_BLOCKING_ENVIRONMENT`；`No logs to publish!`=`NON_BLOCKING_POST_SUCCESS`。
- errors：`[]`。
- unresolved_warnings：`[]`。
- accepted_limitations：上述三项，原始日志未删除。
- S1-R1 状态：`PASS_WITH_LIMITATIONS`。
- PR #3：已 Ready 并普通合并。
- main merge commit：`a028f265c616be922e5ab0ccff907fcbeda06273`。

## B：S1-R2

- 消息合同：`quadrotor_msgs/PolynomialTrajectory`；真实字段见 `docs/evidence/S1-R2/message_contract/`。
- 导出器：`planner_bridge/export/export_am_planner_trajectory.py`，基于源码定义采样，不猜姿态/关节/phase 字段。
- write：19 段，10.4004746152 s，100 Hz，双轨迹 `PASS`。
- grasp：4 段，5.8804546655 s，100 Hz，双轨迹 `PASS`。
- lift：3 段，13.0081347731 s，100 Hz，双轨迹 `PASS`。
- repeat：4 段，5.8804546655 s，100 Hz，双轨迹 `PASS`。
- waypoint variant：`grasp_waypoint_variant_01`，独立 launch overlay 将 `object_px` 从 0.00 改为 0.05；双轨迹 `capture_exit=0`，导出验证 `PASS`。
- 视频：4 个 GIF + 4 个 PNG；GIF 本地保留，PNG 单个小于 2 MB。
- 测试：`pytest planner_bridge/tests -q`：5 passed；独立 audit：`errors=[]`、`warnings=[]`。
- Draft PR：已从 S1-R2 分支创建/更新，保持 Draft，不合并。

## 还缺什么

还缺项目负责人审阅 S1-R2；S1 总体仍缺后续任务卡要求的正式收口，不得据此进入 S2。

## 是否算通过

S1-R2 按允许标签算“提交审阅”，不是整个 S1 PASS：`SUBMITTED_S1_R2_TRAJECTORY_EXPORT`。

## 是否需要项目负责人处理

需要负责人审阅消息合同、导出字段边界、waypoint 变体和可视化；确认后再决定是否授权下一项，当前不自动进入 S2。

## 原始标签

`SUBMITTED_S1_R2_TRAJECTORY_EXPORT`：人话是“轨迹已按真实 ROS 消息结构导出并验证，waypoint 确实改动且重新跑通，证据提交审阅；S1 还没有整体通过”。

## Git

- 开始 Head：`a028f265c616be922e5ab0ccff907fcbeda06273`（PR #3 merge 后 main）。
- S1-R1 最终提交：`78aa715e0825f4495666d447c98d7d75f46790fe`；PR #3 merge：`a028f265c616be922e5ab0ccff907fcbeda06273`。
- main Head：`a028f265c616be922e5ab0ccff907fcbeda06273`。
- S1-R2 分支：`agent/s1-r2-trajectory-export-contract`。
- S1-R2 Head：`8d9d1da`（导出合同、验证、waypoint 和可视化实现提交）；此前 manifest 提交为 `0fbbbe4`。
- 新 PR：Draft，创建后不合并。
- 工作树：提交后保持干净；本地忽略的原始轨迹与 GIF 继续保留。
- stash：`stash@{0}`、`stash@{1}` 保留，未操作。

## 警告分类

1. Catkin：8 个 warning-bearing packages，保留上游/ROS-CMake 原文，`NON_BLOCKING_UPSTREAM`。
2. nvidia-smi：PID/命令行、GPU 指标和 CUDA 日志对齐；进程名 `[Not Found]`，`NON_BLOCKING_ENVIRONMENT`。
3. No logs to publish：优化完成后的发布回调附近出现，随后仍发布双轨迹，`NON_BLOCKING_POST_SUCCESS`。

## 轨迹合同

- 消息类型：`quadrotor_msgs/PolynomialTrajectory`。
- 多项式阶数：使用每段 `order[i]`；四组官方运行均为 5 阶；`num_order=0` 不被误当作实际段阶数。
- 字段：Header、trajectory/action、num_segment、start/final_yaw、coef_x/y/z、time、mag_coeff、order、debug_info。
- unavailable fields：四元数、完整姿态、关节名/关节状态、phase_id、waypoint_id、规划耗时/GPU 指标、带单位的位置字段；见 `unavailable_fields.md`。
- 坐标系/单位：捕获 Header 为 `world`；时间按源码 ROS 秒；位置单位未编码，不伪造。

## 导出

- 任务数：4 组官方 + 1 组 waypoint 变体。
- 文件数：每组 9 个交付文件，轨迹目录合计 45 个文件。
- 采样频率：100 Hz，`sample_dt=0.01`。
- 连续性：位置、速度、加速度边界检查通过，数值容差 `1e-8`。
- NaN/Inf：所有组均 0/0。
- manifest：每组 `sha256_manifest.txt`；视频 `outputs/videos/S1-R2/video_manifest.json`。

## waypoint

- 修改项：grasp 对象/中间约束的 `object_px`。
- 基线：`0.00`。
- 变体：`0.05`，独立 `planner_bridge/variants/grasp_waypoint_variant_01.launch`。
- 双轨迹：`capture_exit=0`，两话题文件存在，数值有限、非零、正持续时间。
- 几何差异：4 段对 4 段；基线 5.8804546655 s，变体 5.1348985021 s；最大位置差约 0.7067484；规划耗时 3572.68 ms 对 5288.42 ms。差异在共同归一化时间网格上比较。

## 视频

- 数量：4 GIF + 4 PNG。
- 路径：`outputs/videos/S1-R2/`、`outputs/figures/S1-R2/`。
- manifest：`outputs/videos/S1-R2/video_manifest.json`，含字节数、SHA-256、帧率、时长和来源。
- 是否提交大视频：否；GIF 保留本地，静态 PNG 均小于 2 MB并提交。

## 自动检查

- pytest：5 passed。
- audit errors：0。
- audit warnings：0。
- git diff --check：通过。
- `check_s0_structure.py`：按任务卡运行；因 S1-R2 分支不满足旧的 `main` 分支断言，并在失败变体目录的 WSL symlink 上触发 Windows `WinError 1920`，退出 1；不作为 S1-R2 通过条件。
- 大文件：S1-R2 轨迹目录无 >10 MB 文件；GIF/PNG 均小于 2 MB。
- 凭据：扫描范围无命中。

## 明确未执行

- 未修改算法：是。
- 未修改系统 ROS：是。
- 未运行 IL/Polynomial_DiT：是。
- 未进入 S2：是。
- 未合并 S1-R2 PR：是。

## 关键证据路径

- `docs/evidence/S1-R2/message_contract/`
- `docs/trajectory_contract.md`
- `data/trajectories/S1-R2/`
- `docs/evidence/S1-R2/waypoint_variant/`
- `docs/evidence/S1-R2/waypoint_variant_comparison.json`
- `docs/evidence/S1-R2/final_acceptance/s1_r2_trajectory_export_audit.json`
- `outputs/videos/S1-R2/video_manifest.json`
- `outputs/figures/S1-R2/`
