# S1-R1 status

- 当前状态：`BLOCKED_S1_R1_ENVIRONMENT`。
- 已完成：PR #2 合并；新建 `AMPlanner-Ubuntu20`（Ubuntu 20.04.3、WSL2）；用户 `amplanner`；ROS Noetic、桌面组件和基础构建依赖安装。
- 未完成：Miniforge/Python 3.8/Autodiff；AM-Planner 固定源码构建；grasp、write、lift 和重复性运行。
- 阻断：官方 Miniforge GitHub 下载在自动重试后返回 `curl: (52) Empty reply from server`。
- 保留：新发行版和全部日志，未修改 AirFAR-Ubuntu20 或其他发行版，未下载 checkpoint，未运行 IL。
