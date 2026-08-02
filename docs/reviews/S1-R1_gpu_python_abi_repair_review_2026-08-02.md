# S1-R1 GPU39 Python ABI 修复总控审查

本轮只处理 Python 3.8/3.9 混链和 GPU39 基础轨迹恢复，不改变算法、任务、launch、YAML、权重或优化参数。

## 固定现场

- 项目分支：`agent/s1-r1-am-planner-install-basic-repro`
- 审查 Head：`b708198f1ad7d18249bb28786db8becc910c0657`
- PR #3：Open + Draft，未合并。
- CPU 和旧 GPU 源码均为 `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d` 且干净。
- 预存的两处未提交审计修改已放入可恢复 stash，未删除。

## 已知根因边界

旧 GPU `se3_node` 的直接 ELF `NEEDED` 同时包含 `libpython3.8.so.1.0` 与 `libpython3.9.so.1.0`；`libse3_planner.so` 直接包含 Python 3.8。`/opt/ros/noetic/lib/libroslib.so` 自身不直接依赖 Python 3.8，因此允许先尝试零源码 CMake 配置修复，失败时才考虑 plan_manage 的最小 CMake 兼容补丁。

## 硬边界

- 新 GPU39 工作区必须没有旧 build/devel/log/cache。
- ABI 门禁要求 `se3_node` 仅有 Python 3.9，且解释器探针的 `sys.path` 不含 Python 3.8。
- write 是第一运行门；write 未通过不得运行 grasp/lift/重复性。
- 不使用 `LD_PRELOAD`、符号链接、`patchelf` 或二进制修改；不重编系统 ROS。
- S2–S8、IL、Polynomial_DiT、第三方源码提交和 PR 合并保持冻结。
