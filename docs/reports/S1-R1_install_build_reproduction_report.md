# S1-R1 安装、构建与基础复现报告

## 结论

本轮恢复了官方下载路径并完成了 Python 3.8、`autodiff` 和固定源码准备，但尚未能成功编译，因此三项规划示例没有启动，更没有轨迹成功证据。

## 已完成

- 官方 Miniforge `26.3.2-2` 由 Windows GitHub CLI 下载，文件为 106,038,245 字节；官方校验值、任务卡固定值和实测 SHA-256 均为 `42260ffe3830fb953d5eee1bbb32229ff06aa7c3833c1ed7a9a0420a95685d94`。
- 已在 `AMPlanner-Ubuntu20` 安装 Miniforge；已创建 `am-planner-py38`，验证 Python `3.8.20` 与 `autodiff 1.1.2`。
- WSL GitHub TLS 中断后，使用 Windows 官方 GitHub CLI 获取源码并以 Git bundle 传入 WSL ext4；Linux 工作区远端仍指向官方仓库，HEAD 为 `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`，工作树干净。
- 已将 requirements 分为 Basic 与 IL 冻结清单；没有安装 `torch`、`torchvision`、`triton`。

## 构建阻断

- 第一次 `catkin build` 未成功。详细复现显示 Conda 中的 `catkin-tools 0.9.4` 在加载工作区时出现 `KeyError: _Context__extend_path`，尚未进入 AM-Planner 编译。
- 尝试使用系统 `catkin` 时，发现该发行版未安装 `/usr/bin/catkin`。因此不能把工具启动失败说成源码构建通过，也不能开始 grasp、write、lift。

## 未执行

未运行 grasp、write、lift 或重复性测试；未捕获 `/trajectory` 或 `/trajectory_arm`；未修改 AM-Planner 核心源码；未修改 AirFAR 或其他 WSL；未下载 checkpoint；未运行 IL；未进入 S2；未合并 Draft PR #3。

## 关键证据

- `docs/evidence/S1-R1/miniforge_download_manifest.json`
- `docs/evidence/S1-R1/miniforge_windows_sha256.txt`
- `docs/evidence/S1-R1/miniforge_install_log.txt`
- `docs/evidence/S1-R1/conda_environment_setup_log.txt`
- `docs/evidence/S1-R1/am_planner_source_manifest.txt`
- `docs/evidence/S1-R1/build_attempt_01.log`
- `docs/evidence/S1-R1/build_attempt_01_octomap_server_verbose.log`
