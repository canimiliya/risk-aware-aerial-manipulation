# S1-R1 R7-R3-R1 执行授权记录

依据用户提供的 `R7-R3-R1_低级Agent_状态门槛处理_完整ABI与GPU轨迹验收_任务卡.md` 执行。

本轮授权范围：

- 在当前仓库 `.git/info/exclude` 中追加 `/.coordination/`；保留、不删除、不提交 `.coordination/`。
- 在隔离 WSL 路径 `/home/amplanner/ros-noetic-py39-overlay-r7r3-r1` 构建 ROS Noetic Python 3.9 overlay。
- 在隔离 AM-Planner clone `/home/amplanner/am-planner-r7r3-r1-ws` 中仅修改 `src/plan/traj_opt/CMakeLists.txt` 和 `src/plan/plan_manage/CMakeLists.txt`。
- 在完整 ABI 门槛通过后运行 GPU write；write 通过后运行 grasp、lift 和 grasp 重复性。
- 保存正式证据、审计并保持 PR #3 为 Draft；不合并、不进入 S2。

本轮明确不授权或任务卡禁止：修改算法/任务参数/系统 ROS/驱动/CUDA，操作旧工作区和 stash，使用 `patchelf`/`LD_PRELOAD`/伪造 Python 库链接，提交第三方源码或构建产物，force push、rebase、reset hard、git clean。
