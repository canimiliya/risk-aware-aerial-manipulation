# S2-R3 机体与旋翼代理合同

- 官方 `arm.xacro`：`body` 使用 `package://delta_display/meshes/drone.dae`（`arm.xacro:1-33`），但该 URDF 片段不声明 rotor center/radius。
- body sphere `0.20 m` 与 rotor disk radius `0.25 m` 沿用 S2-R0 的 `PROVISIONAL_S2_ASSUMPTION`，没有将 Delta static radius `0.08 m` 误当成无人机机体半径，也没有缩小半径以通过门槛。
- rotor centers `[±0.17,±0.17,0.05] m`、disk radius `0.25 m` 是 `PROVISIONAL_S2_ASSUMPTION`；body/rotor 姿态随 `R_WB(t)` 旋转。
- 上臂、下部杆使用官方 `getJointPoints` 中心线的 `0.010 m` capsule；moving platform/end-effector 使用 `0.025 m` 官方任务代理。
