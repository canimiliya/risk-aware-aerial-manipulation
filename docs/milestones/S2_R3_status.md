# S2-R3 状态：SUBMITTED_FOR_REVIEW / SUBMITTED_S2_R3_IK_FAILED

## 结论

S2-R3 已完成官方执行层合同、IK/FK、FlatnessMap、连续关节回放和全身代理碰撞验证，并提交复核。官方 IK 数值回环和姿态映射通过，但真实 S2-R2 轨迹的官方 `[0,π/2]` joint branch 与 body `0.20 m` full-body proxy gate 失败，因此不能标记 `S2_R3_FULL_BODY_PROXY_READY`。

## 当前状态

- `S2-R3：SUBMITTED_S2_R3_IK_FAILED`，review state 为 `SUBMITTED_FOR_REVIEW`。
- `S2：IN_PROGRESS`；`S3–S8：FROZEN`。
- 失败证据、narrow、nominal/repeat 和所有频率结果保留；未修改官方算法、URDF/Xacro、ROS、Conda 或 gate。

## 下一步边界

项目负责人需要先决定是否接受该失败证据并授权返工轨迹/执行层合同；本轮不自动修正规划器、不重新规划、不进入 S3 或 Isaac Lab。
