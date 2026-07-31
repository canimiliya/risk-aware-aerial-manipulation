# S1-R1 status

- 当前状态：`BLOCKED_S1_R1_BUILD`（环境和固定源码已准备好，但 Catkin 构建工具不能正常进入编译）。
- 已完成：官方 Miniforge 26.3.2-2 经 Windows GitHub CLI 下载并双重校验；隔离 WSL 内安装成功；Python 3.8.20、`autodiff 1.1.2`、基础 Python 依赖与固定 AM-Planner 源码均已就绪。
- 构建事实：Conda 中的 `catkin-tools 0.9.4` 在加载工作区时抛出 `KeyError: _Context__extend_path`；尝试系统 Catkin 时确认发行版没有 `/usr/bin/catkin`。未修改 AM-Planner 源码。
- 未完成：Catkin 成功构建、grasp/write/lift、轨迹消息和重复性证据。
- 保留边界：未修改 AirFAR 或其他发行版；未下载 checkpoint；未运行 IL；未安装 torch、torchvision、triton；PR #3 仍为 Draft。
