# S2-R0 Delta 臂官方来源清单

## 固定来源

- AM-Planner commit：`7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。
- 本地只读副本：`third_party/am-planner/`（Git 忽略，不向官方源码写入）。
- URDF/Xacro：`src/uam_sim/delta-display/delta_display/urdf/arm.xacro`。
- 关节名配置：`src/uam_sim/delta-display/delta_display/config/joint_names_arm6.yaml`。
- FK/IK/连杆点：`src/uam_sim/delta-display/delta_display/src/delta_display.cpp`，函数 `FK_kin`、`IK_kin`、`getJointPoints`。
- 参数来源：`src/plan/plan_manage/launch/run_in_sim_grasp.launch` 与 `misc/grasp.yaml`。

## 事实边界

官方模型是三主动转动关节、六条被动/初始化锁定的 trailing-arm 连接的 Delta 机构。源码的 FK 输出是 `A0` 局部坐标中的平台位置；源码没有给出用于本项目任务规划的完整末端姿态语义、工具几何或电力横担尺寸。后者全部标记为 `PROVISIONAL_S2_ASSUMPTION`，未伪装成官方参数。
