# S1-R1 环境阻断审查

- 审查 Head：`f705514fb85fdba6a37868d36b1752dd8b0ee457`
- 当前结果：隔离 Ubuntu 20.04 与 ROS Noetic 已成功，默认用户为 `amplanner`。
- 未完成：Miniforge、Python 3.8、`autodiff`、AM-Planner 构建和三项示例运行。
- 根因：WSL 内从 GitHub release 下载 Miniforge 时返回 `curl: (52) Empty reply from server`。
- 判断：这不是 ROS 安装失败，也不是 AM-Planner 源码失败。
- 处理决定：由 Windows GitHub CLI 下载固定官方 Miniforge release，校验 SHA-256 后经 `/mnt/d` 传入隔离 WSL。
- 分支与评审：继续使用 `agent/s1-r1-am-planner-install-basic-repro` 和 Draft PR #3。
- 冻结范围：不下载 Polynomial_DiT checkpoint，不运行 IL。
