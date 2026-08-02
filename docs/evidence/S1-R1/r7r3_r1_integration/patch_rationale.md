# AM-Planner Python 3.9 ABI 补丁说明

固定基线：官方 AM-Planner commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`，归档 SHA-256 为 `4D4A923907047E2B3FD47B84E54892F988A4439DFBC56EAF81A155D4E9042D59`。

仅修改：

- `src/plan/traj_opt/CMakeLists.txt`
- `src/plan/plan_manage/CMakeLists.txt`

处理原则：

- 两个包都用 `find_package(Python3 3.9 EXACT REQUIRED COMPONENTS Interpreter Development)`。
- 两个包都用 `find_package(pybind11 CONFIG REQUIRED)`。
- 将 `${catkin_LIBRARIES}` 复制到包局部变量；仅用正则过滤 `python3.8`，不移除任何 ROS 库。
- 显式加入 `Python3::Python` 和 `pybind11::embed`，并把 Python 3.9 include 目录加入目标。
- 未修改 C++、头文件、算法、任务点、launch、权重或优化器参数。

正式补丁及 SHA：`am_planner.patch`、`patch_sha256.txt`。
