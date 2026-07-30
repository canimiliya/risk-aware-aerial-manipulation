# S1-R1 隔离安装、构建与基础复现报告

## 结论

本轮已完成 S1-R0 的 PR #2 普通合并，并建立独立 Ubuntu 20.04 WSL 与 ROS Noetic 基础环境；尚未建立 Python 3.8/Autodiff，因此没有构建 AM-Planner 或运行三项官方 Basic 示例。

状态为 `BLOCKED_S1_R1_ENVIRONMENT`：官方 Miniforge 安装器从 GitHub 下载时在自动重试后返回 `curl: (52) Empty reply from server`。该错误原始日志已保留，未用非官方镜像替代，也未安装 IL 依赖。

## 已完成事实

- PR #2 merge commit：`44273a990c5ebc4c0c3ec13dc0332ffe90e16798`。
- 新发行版：`AMPlanner-Ubuntu20`，位置 `D:\\WSL\\AMPlanner-Ubuntu20`，Ubuntu 20.04.3，WSL2，默认用户 `amplanner`。
- 官方 Ubuntu 20.04 Appx SHA-256：`BE91806D4C9250EB275CAFB3559AA44257F320564A17A824D29D5F937BE42025`。
- ROS Noetic 已验证；其 EOL 后仍由 `packages.ros.org` 托管，但不再有官方功能、安全或 bug 修复支持。本环境仅用于固定科研复现。
- `rosdep update` 因旧 Fuerte 元数据下载超时未完整成功；其原始日志已保存。

## 未执行

未下载 Polynomial_DiT checkpoint；未运行 IL；未修改 AM-Planner 源码；未修改 AirFAR-Ubuntu20 或其他 WSL；未构建 AM-Planner；未运行 grasp、write、lift；未进入 S2。

## 关键证据

- `docs/evidence/S1-R1/official_image_manifest.json`
- `docs/evidence/S1-R1/wsl_install/import_manifest.json`
- `docs/evidence/S1-R1/ros_package_manifest.txt`
- `docs/evidence/S1-R1/rosdep_update.txt`
- `docs/evidence/S1-R1/conda_install_log.txt`
