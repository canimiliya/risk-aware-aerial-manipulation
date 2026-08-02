# S1-R1 R7-R3-R1 Python 3.9 overlay、完整 ABI 与 GPU 轨迹验收

## 结论

本轮已完成任务卡授权范围内的状态门槛、官方 ROS Python 3.9 overlay、AM-Planner 两文件 CMake ABI 修复、19 包构建、完整 ABI、嵌入式 GPU 探针，以及 write → grasp → lift → grasp 重复性运行。四个成功运行均捕获 `/trajectory` 与 `/trajectory_arm`，数值有限且无 NaN/Inf。

本轮提交状态为 `SUBMITTED_FOR_REVIEW`，不是 PASS。审计硬错误为 0；仍有三类必须公开保留的告警：Catkin 报告 8 个 warning-bearing packages；`nvidia-smi` 进程名返回 `[Not Found]`（但 se3 PID 被采样、GPU 利用率为 10–13%、roslaunch 明确显示 CUDA 初始化）；程序结束时有非致命的 `[MANAGE]: No logs to publish!`。

## 已完成

- `.coordination` 未删除、未跟踪、未提交；`.git/info/exclude` 仅追加本地 `/.coordination/` 规则。清单为 19 文件、73,881 bytes。
- ROS overlay 位于 `/home/amplanner/ros-noetic-py39-overlay-r7r3-r1`，使用官方 `ros/rospack` commit `fd4d6fd87895c389c58b52e4009fe0b793769818` 和 `ros/ros` commit `99fd9bb76338f3315cd0a89af700d789ef337ea6` 的冻结归档；没有使用镜像。
- AM-Planner 固定 base commit 为 `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`，只修改 `src/plan/traj_opt/CMakeLists.txt` 与 `src/plan/plan_manage/CMakeLists.txt`；patch SHA256 为 `8bd9fa32c508495bd1f98f77b529205323ecbdf59c9031be2ec75790c33f7db6`。
- 构建发现 19 个项目包，0 failed、0 abandoned；Catkin 汇总含 `catkin_tools_prebuild` 为 20 succeeded，另有 8 个包带 warning，故不宣称 errors=0/warnings=0。
- `libse3_planner.so`、`se3_node`、overlay `librospack.so` 均直接 NEEDED Python 3.9；完整闭包 Python 3.8 occurrence 为 0，运行时 `not found` 为 0。
- 嵌入式探针：Python 3.9.23、Torch 2.7.1+cu128、CUDA True、NVIDIA GeForce RTX 5060 Ti、capability `(12, 0)`，normal 与 `env -i` 均通过。

## 运行结果

| 任务 | 成功运行 | 轨迹结构 | 总持续时间 | 规划耗时 | 结果 |
|---|---|---:|---:|---:|---|
| write | `write_r7r3_r1_gpu_run_02` | 19 段 / 19 段 | 10.4005 s | 原始日志保留 | 双轨迹成功 |
| grasp | `grasp_r7r3_r1_gpu_run_02` | 4 段 / 4 段 | 5.88045 s | 3572.68 ms | 成功 |
| lift | `lift_r7r3_r1_gpu_run_01` | 3 段 / 3 段 | 13.0081 s | 2722.31 ms | 成功 |
| grasp repeat | `grasp_r7r3_r1_gpu_run_03` | 4 段 / 4 段 | 5.88045 s | 3374.95 ms | 成功 |

write 的两个话题各有 390 个数值字段，NaN=0、Inf=0；grasp/lift/重复 grasp 同样全部通过有限数值、非零值和正持续时间检查。write 原始日志包含 JPS 搜索、MINCO setup、Finish optimization 和 CUDA 初始化。第一次 write 的运行器环境失败、第一次 grasp 的参数顺序失败均作为历史失败证据保留，没有覆盖。

## 基线与边界

CPU/旧 GPU/旧 GPU39 工作区、系统 ROS、CPU/GPU Conda 与 stash 未通过本任务修改；旧 runner 进程被发现后保持原状。没有修改算法、任务点、launch、YAML、优化参数或权重，没有运行 IL/Polynomial_DiT，也未进入 S2。

## 审计

专用审计 `scripts/audit/check_s1_r1_r7r3_r1.py` 输出 `errors=[]`、3 条明确 warnings，决策为 `SUBMITTED_R7R3_GPU_OFFICIAL_BASIC_REPRO`。关键 JSON 输出见 `docs/evidence/S1-R1/r7r3_r1_state_gate/r7r3_r1_audit.json`。

## 关键证据

- 状态门槛：`docs/evidence/S1-R1/r7r3_r1_state_gate/`
- ROS overlay：`docs/evidence/S1-R1/r7r3_r1_ros_overlay/`
- AM-Planner/ABI/探针：`docs/evidence/S1-R1/r7r3_r1_integration/`
- GPU 运行：`docs/evidence/S1-R1/r7r3_r1_runtime/`
