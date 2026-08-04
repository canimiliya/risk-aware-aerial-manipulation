# S3-R0 status

- S3：`SUBMITTED_S3_R0_PLAYBACK_FAILED`
- 轨迹协议：`PASS`
- Isaac Sim/Isaac Lab 基础运行：`READY_WITH_LIMITATIONS`
- 机器人导入与场景：`PASS_WITH_LIMITATIONS`
- FK：`PASS`（使用项目 `official_fk_joint_state`）
- PhysX scene-query：`PASS_WITH_LIMITATIONS`
- 精确 clearance/repeat/GUI：`NOT_COMPLETE`
- S4--S8：`FROZEN`

本轮修正了上一版播放脚本错误的 FK convention：协议 `q_rad` 必须经过 `official_fk_joint_state`，修正后 arm/world EE 残差分别为 `1.39e-16 m` 和 `2.22e-16 m`。由于官方导入 USD 没有可初始化的完整 articulation root，采用任务卡允许的 `S3_KINEMATIC_PLAYBACK_ARTICULATION`；通过 USD PhysicsJointStateAPI 写入/读回三 active joints，并关闭关节物理约束以避免未建模闭链动力学污染 reference playback。

nominal 1046 帧播放和 PhysX overlap query 均完成：非场景自身重叠以外无命中，0.010 m 扩展盒无机器人命中，穿透记录为 0。但当前 query 只提供 clearance 下界，未提供精确最小距离和 S2 delta；nominal repeat、GUI、8 PNG/2 video 也未完成。因此不宣称 S3 PASS，也不进入 S4。
