# S1-R1-R7-R1 GPU39 Python ABI 修复报告

结论：完成了根因追踪、全新 GPU39 工作区构建和任务卡允许的最小 CMake 补丁测试；仍存在 `libse3_planner.so -> libpython3.8` 的传递 ABI，ABI 硬门槛未通过，所以没有运行 write、grasp、lift，也没有推送或合并 PR。

当前做到的：

- CPU 与旧 GPU 工作区保持原状；源码仍为固定 commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。
- 新 GPU39 工作区从官方仓库干净克隆；没有复制旧 build/devel/cache。
- 零源代码配置版构建达到 19/19；补丁版在关闭 `CMAKE_LINK_WHAT_YOU_USE` 的诊断构建中也达到 19/19。
- 已保存旧 GPU 根因链、补丁、SHA256、补丁后 ELF/link/CMake 证据。
- 补丁后 `se3_node` 直接 NEEDED 只有 Python 3.9；但 `libse3_planner.so` 仍直接 NEEDED Python 3.8，`ldd` 仍同时解析 3.8 与 3.9。
- GitHub PR #3 仍是 Open + Draft；没有 push、rebase、force push 或合并。

还缺什么：

- 在不扩大任务卡允许的源码边界的情况下，无法把 `libse3_planner.so` 的 Python 3.8 依赖移除。
- 因此解释器探针、write 1200 秒、grasp/lift/重复性验收均未执行。

是否算通过：不通过。构建通过不等于 ABI 通过；当前属于硬门槛阻塞。

是否需要我处理：需要你决定是否授权扩大补丁边界到 `traj_opt/CMakeLists.txt`（这会超出本任务卡原授权）。未授权前我会保持停止，不运行 write。

原始标签：`BLOCKED_S1_R1_GPU_PYTHON_ABI_REPAIR`（人话：允许的单文件补丁只能修掉 se3_node 的直接链接，修不掉下游共享库带来的 Python 3.8，所以不能进入轨迹验收）。
