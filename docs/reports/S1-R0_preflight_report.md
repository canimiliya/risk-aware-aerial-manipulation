# S1-R0：AM-Planner 环境与源码只读预检报告

## 范围与结论

- S0 main merge commit：`58724118d4f857dc0b3bd23c4d415e70219b853e`；本分支基准相同。
- 本轮未安装、未创建 Conda 环境、未下载 checkpoint、未运行规划、未训练。
- 结论：`SUBMITTED_S1_PREFLIGHT`；允许高级总控据此设计 S1-R1 安装与官方基础示例复现任务，但不构成安装授权。

## WSL 和候选环境

`wsl --version`、`--status`、`--list --verbose`、`--list --running` 全部在 30 秒内退出，原始 JSON 位于 `docs/evidence/S1-R0/`。五个目标发行版均成功执行无 profile 的只读探针：Ubuntu-24.04=24.04.4、Ubuntu=26.04、NMPC-Ubuntu22=22.04.5、dbLaCAM-Ubuntu=24.04.4、AirFAR-Ubuntu20=20.04.6。

AirFAR-Ubuntu20 连续本轮多次命令均成功；`/opt/ros/noetic` 存在、`ros-noetic-ros-base` 为 `1.5.0-1focal.20250521.010531`、根分区约 949 GB 可用，未在探针深度内发现 AM-Planner/Polynomial_DiT/catkin 目录。它是既有 AirFAR 项目环境，故策略为 `CREATE_NEW_ISOLATED_UBUNTU20_RECOMMENDED`，而非复用批准。

## AM-Planner 固定源码审计

- 仓库：`https://github.com/SYSU-HILAB/am-planner.git`；Windows 与 AirFAR WSL 的 `git ls-remote` 均成功。
- 固定 commit：`7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。本地只读副本在 `third_party/am-planner/`（被 Git 忽略）；Windows 长路径导致一个嵌套 Boost 头未落盘，记录于 `am_planner_repo_state.txt`，不影响已读取的核心静态文件，但也说明正式 WSL 工作区应避免 Windows 路径限制。
- README 声明 MIT，但冻结 commit 根目录没有 `LICENSE`；`.gitmodules` 不存在，`git lfs ls-files` 无输出。该许可证限制继续沿用 S0 分离记录，不能当作已验证 MIT 文件。
- `shfiles/run.sh` 的三个选项是 grasp、strike、other；默认启用 grasp。Basic planning 的 `run.sh` 仅 source 工作区并启动 ROS launch，不调用 Polynomial_DiT checkpoint。`shfiles/il.sh` 才启动 `shfiles.il_guided`。
- 推荐首批官方基础任务：grasp、other/write、other/lift；三者应在 S1-R1 逐个短运行、保留命令和 ROS 日志。它们不应启用 IL。
- 源码列出的构建路径需要 ROS/catkin、Python 3/pybind11/autodiff、Eigen/Boost/octomap，以及 `roscpp`、`rospy`、`std_msgs`、`octomap_server`、`jps3d`、`decomp_ros_utils`、`quadrotor_msgs`、`visualization_msgs`、`vis_utils` 等包；完整清单在静态提取证据。CUDA 11.8 在 README 中为 Recommended；基础 launch 无 checkpoint 入口，因此不是基础复现已证实的硬依赖。
- 轨迹通过 `/trajectory` 与 `/trajectory_arm` 发布，消息类型线索为 `quadrotor_msgs/PolynomialTrajectory`；RViz 可视化话题包含 `/visualization/trajectory*`。本轮没有运行以验证日志/视频产物。

## Polynomial_DiT

固定 commit 为 `f31c8f04e5fa045bc08c7bbaaadfe60bb54816f1`。静态 README 与 `checkpoints/download.py` 指向 Hugging Face `dwl1437/Polynomial-DiT`，使用 `huggingface_hub.snapshot_download`，未见 token 参数；文件大小和模型许可证无法从已读源码可靠推断，且冻结树中未发现 LICENSE。基础规划可暂时绕过。若后续必须使用，须在隔离环境中先审计 Hugging Face 文件、访问要求、许可证、哈希和下载大小，严禁公开再分发。

## 风险与下一步

阻断安装的不是 WSL 可用性或源码可达性，而是尚未获准的正式安装任务。LongPathsEnabled=0 仍是 Windows 本地工作副本限制；新建隔离 WSL 工作区可规避它。建议仅设计 S1-R1：在新隔离 Ubuntu 20.04 中安装固定依赖、构建、逐项运行三项基础任务；IL/checkpoint 保持冻结。

