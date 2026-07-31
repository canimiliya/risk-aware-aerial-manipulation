# S1-R1 安装、构建和基础运行报告

## 结论

环境和 19 个包的构建已经复核成功，但基础轨迹运行没有通过。原因不是猜测：官方规划节点完成路径搜索后要求 Python `torch`，而本任务禁止安装它，也禁止修改官方源码绕开它。

## 当前做到的

- Miniforge 26.3.2-2、Python 3.8.20、autodiff 1.1.2 已保留在隔离发行版中。
- AM-Planner 固定在 `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`，工作树干净。
- `/usr/bin/catkin` 的增量构建为 19/19 成功、退出码 0。此前 Conda 自带 catkin 的 `KeyError: _Context__extend_path` 没有再用；系统 catkin 负责构建，Conda 仅提供 Python/autodiff 的 CMake 前缀。
- 运行器为每次运行建立独立 ROS master、ROS_HOME、PID 和日志目录；捕获器在 launch 前启动，订阅 `/trajectory` 与 `/trajectory_arm`。
- grasp 三次尝试均已保留：首次为运行器 source 顺序问题；第二次发现缺少地图 Python 依赖；第三次在地图、规划器和两条话题都已启动后，因缺少 `torch` 被官方节点 abort。

## 还缺什么

- grasp/write/lift 的两条非空轨迹消息、数值检查和 grasp 重复性都未完成。
- 未安装 torch/torchvision/triton，故不能解除当前阻塞。

## 是否需要我处理

需要你只决定一件事：是否允许为这个官方运行入口安装它明确要求的 torch 运行依赖。若不允许，本轮应按运行时受限结案，不应宣称基础复现通过。

## 证据

- 构建：`docs/evidence/S1-R1/build_final/build_runtime_gate.log`
- grasp 运行与失败：`docs/evidence/S1-R1/runtime/s1-r1-runtime/grasp_run_01_retry_03/roslaunch.log`
- 消息未收到的机器可读结果：`docs/evidence/S1-R1/runtime/s1-r1-runtime/grasp_run_01_retry_03/numeric_validation.json`
- 运行时阻塞摘要：`docs/evidence/S1-R1/runtime_blocker_summary.md`

## 原始标签

`SUBMITTED_S1_R1_BUILD_WITH_RUNTIME_BLOCKER`：构建成功，但运行被禁止安装的依赖拦住。
