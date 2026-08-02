# GPU39 ABI 兼容补丁说明

- 基线：`7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。
- 触发条件：零源代码配置后，`se3_node` 的直接 ELF NEEDED 仍同时出现 Python 3.8 和 3.9；`/opt/ros/noetic/lib/libroslib.so` 本身没有直接 Python 3.8 依赖，因此满足任务卡允许补丁的前提。
- 唯一改动：只改 GPU39 clone 的 `src/plan/plan_manage/CMakeLists.txt`，从 `catkin_LIBRARIES` 局部移除 `libpython3.8`，并把 `pybind11::embed` 放在前面，使 `se3_node` 直接链接 Python 3.9。
- 未改动：CPU 工作区、旧 GPU 工作区、任何 `.cpp/.h`、任务点、launch、YAML、权重、优化参数、CUDA/ROS 系统安装。
- 验证结果：补丁版 `se3_node` 直接 NEEDED 只剩 `libpython3.9.so.1.0`，但其直接依赖的 `libse3_planner.so` 仍 NEEDED `libpython3.8.so.1.0`；因此运行时仍同时装载两个 Python ABI。为验证链接本身，关闭 `CMAKE_LINK_WHAT_YOU_USE` 后得到 19/19；任务卡要求的 TRUE 配置在该补丁版的 `plan_manage` 链接阶段出现 CMake `__run_co_compile --lwyu` 的 `undefined reference to main`，不能据此宣称硬门槛通过。
- 结论：补丁已证明能消除 `se3_node` 的直接旧 Python 链接，但在任务卡限定的单文件边界内无法消除 `libse3_planner.so` 的 Python 3.8 传递依赖；因此不启动解释器正式探针和 write。
