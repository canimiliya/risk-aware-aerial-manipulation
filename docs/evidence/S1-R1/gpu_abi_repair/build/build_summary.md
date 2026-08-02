# 构建摘要

- 零源代码配置：19/19 成功；日志原件保留在 WSL 新工作区 `/home/amplanner/am-planner-gpu39-ws/logs/`，未放入项目 Git。
- 允许补丁 + `CMAKE_LINK_WHAT_YOU_USE=TRUE`：18/19，`plan_manage` 在 CMake `__run_co_compile --lwyu` 阶段报 `undefined reference to main`。
- 允许补丁 + `CMAKE_LINK_WHAT_YOU_USE=FALSE` 诊断构建：19/19，得到可分析的 `se3_node`。
- 诊断构建不是任务卡最终硬门槛替代；最终配置已恢复为任务卡要求的 `CMAKE_LINK_WHAT_YOU_USE=TRUE`。
- 补丁后 ELF：`se3_node` 直接 NEEDED 仅 Python 3.9；`libse3_planner.so` 仍直接 NEEDED Python 3.8；带 GPU39 `LD_LIBRARY_PATH` 时 ldd 同时解析两者。
