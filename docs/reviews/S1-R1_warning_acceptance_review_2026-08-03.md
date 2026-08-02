# S1-R1 三项告警接受审查（2026-08-03）

## 结论

三项告警均有原始证据，当前没有发现会阻断四次成功双轨迹运行的证据。因此本轮将它们记录为 `accepted_limitations`，不是把日志过滤成无告警；`unresolved_warnings` 为空。Catkin 的 8 个 warning-bearing packages 由原始 Catkin 输出自动解析，清单见 `docs/evidence/S1-R1/final_warning_triage/catkin_warning_inventory.{json,md}`。

## 1. Catkin 8 个 warning-bearing packages

- 分类：`NON_BLOCKING_UPSTREAM`。
- 原始来源：`docs/evidence/S1-R1/r7r3_r1_integration/build_attempt_02.log`。
- 精确包名与原始 warning marker 数量：`octomap_server` 10、`map_pcl` 4、`so3_control` 2、`so3_quadrotor_simulator` 2、`traj_server` 7、`jps3d` 14、`traj_opt` 11、`plan_manage` 2。
- 原文摘要包括 CMake `add_library/add_executable`、PCL 的 pcap/png/libusb 功能禁用、上游源码的 `-Wsign-compare`、`-Wunused-variable`、`-Wformat` 和枚举比较提示。
- 未发现 Python 3.8、未解析符号、runtime not-found、CUDA 架构或轨迹数据 warning；完整 ABI 和运行检查另见 `docs/evidence/S1-R1/r7r3_r1_integration/` 与 `docs/evidence/S1-R1/r7r3_r1_state_gate/r7r3_r1_audit.json`。
- 本轮不修改算法 `.cpp/.h`，也不删除原始 warning。

## 2. nvidia-smi `[Not Found]`

- 分类：`NON_BLOCKING_ENVIRONMENT`。
- 原始证据：`docs/evidence/S1-R1/r7r3_r1_runtime/write_r7r3_r1_gpu_run_02/snapshot_60s.json`、`monitor_samples.jsonl`、`monitor_summary.json`、`roslaunch.log`。
- `snapshot_60s.json` 同时记录了运行中的 `se3_node` PID `85559`、其命令行为 `.../plan_manage/se3_node`，以及 `nvidia-smi pmon` 原文 `85559, [Not Found], [N/A]`。
- 同一运行窗口的 GPU 利用率为 10–13%，显存为 2047–2386 MB；`roslaunch.log` 原文包含 `Using device: cuda`。因此 GPU 使用证据来自 PID/命令行、进程窗口、GPU 指标和进程内 CUDA 日志的组合，不把 `[Not Found]` 单独当作 GPU 证据。
- 限制：本次历史快照没有保存 `/proc/<PID>/exe` 的独立文件，因此保留“进程名不可读”的环境限制，不宣称 nvidia-smi 进程名验收通过。

## 3. `[MANAGE]: No logs to publish!`

- 分类：`NON_BLOCKING_POST_SUCCESS`。
- 原始证据：四次成功运行的 `roslaunch.log` 和对应 `ros_home/log/*/rosout.log`。
- 四次日志均先出现 `Finish optimization!`，随后在同一发布回调附近出现 `[MANAGE]: No logs to publish!`，紧接着出现 `[MANAGE]: The trajectory is published!`；对应 `processes.json` 的 `capture_exit=0`，且 `/trajectory` 与 `/trajectory_arm` 均有完整有限数值数据。
- 该字符串实际位于最终发布前的日志发布分支，不能改写成“日志中没有 error”；接受依据是两条轨迹仍成功发布、文件未缺失、数值验收成功，而不是删除该文本。
- 代表性原文：`write_r7r3_r1_gpu_run_02/roslaunch.log:15454-15466`；grasp、lift、repeat 的对应原文行号见最终审计 JSON。

## 接受边界

接受以上三项限制只表示它们不阻断本次 S1-R1 的轨迹基础复现；不表示源码质量告警被修复、不表示 nvidia-smi 进程名可读、不表示整个 S1 PASS。S1-R1 只能收口为 `PASS_WITH_LIMITATIONS`，S1 继续 `IN_PROGRESS`，S2–S8 继续 `FROZEN`。
