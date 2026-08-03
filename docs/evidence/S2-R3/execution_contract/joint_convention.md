# S2-R3 关节约定

- 主动关节：`m1_1,m2_1,m3_1`；来源 `arm.xacro:130-268`。
- `DeltaDisplay::endCallback` 发布的 `sensor_msgs/JointState.position` 顺序与 `joint.name={m1_1,m2_1,m3_1}`（`delta_display.cpp:114-116`）一致。
- 官方执行层 IK 分支范围为 `[0, π/2]`（`delta_display.cpp:376-387`）。URDF revolute limit 为 `[-1.57,1.57]`，但本轮以更严格的官方 IK 工作分支作为硬检查。
- `qdot/qddot` 是离线轨迹数值导数，不是执行器动力学或电机控制验证。
