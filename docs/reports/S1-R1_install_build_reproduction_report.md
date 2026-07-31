# S1-R1 安装、构建和基础运行报告

## 结论

官方 CPU Torch 已安装、仓库自带权重已验证可加载、19/19 构建仍成功；但三项基础轨迹运行仍未通过。grasp 在 JPS 和 MINCO 初始化后由官方节点 abort，未产生任何真实双轨迹消息。

## 当前做到的

- Miniforge 26.3.2-2、Python 3.8.20、autodiff 1.1.2 与官方 CPU `torch==2.4.1+cpu` 已保留在隔离发行版中；CUDA 未启用。
- AM-Planner 固定在 `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`，工作树干净。
- `/usr/bin/catkin` 的增量构建为 19/19 成功、退出码 0。此前 Conda 自带 catkin 的 `KeyError: _Context__extend_path` 没有再用；系统 catkin 负责构建，Conda 仅提供 Python/autodiff 的 CMake 前缀。
- 运行器为每次运行建立独立 ROS master、ROS_HOME、PID 和日志目录；捕获器在 launch 前启动，订阅 `/trajectory` 与 `/trajectory_arm`。
- `torch.nn`、autograd 和仓库自带工作空间权重均已独立验证；未安装 torchvision、torchaudio 或 triton。
- grasp 的三次正式尝试均已保留：点云、JPS 和 MINCO 初始化完成后，官方 `se3_node` 以 abort（退出码 -6）结束。两条话题类型可见，但三次均未捕获任何消息。

## 还缺什么

- grasp/write/lift 的两条非空轨迹消息、数值检查和 grasp 重复性都未完成。
- grasp 未过门槛，按任务卡不得继续 write、lift 或 grasp 重复性。

## 是否需要我处理

需要你决定是否授权下一轮仅诊断官方 `se3_node` 的 abort 根因；本轮没有修改 AM-Planner 源码，也不应把它写成基础复现通过。

## 证据

- Torch 与权重：`docs/evidence/S1-R1/torch_runtime/`
- 构建：`docs/evidence/S1-R1/build_after_torch/build_after_torch.log`
- grasp 运行与消息检查：`docs/evidence/S1-R1/runtime/grasp_torch_run_01_retry_03/`

## 原始标签

`SUBMITTED_S1_R1_BUILD_WITH_RUNTIME_BLOCKER`：构建成功，但运行被禁止安装的依赖拦住。
