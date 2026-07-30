# 离线轨迹协议草案

状态：`DRAFT_NOT_IMPLEMENTED`。必需 SI 字段：`time`、`base_position_world[3]`、`base_quaternion_world[4]`、`base_linear_velocity_world[3]`、`base_angular_velocity_body[3]`、`arm_joint_position[n]`、`arm_joint_velocity[n]`、`end_effector_position_world[3]`、`end_effector_quaternion_world[4]`、`end_effector_linear_velocity_world[3]`、`phase_id`。待冻结：坐标系元数据与四元数顺序。验收将检查时间严格单调、四元数归一化、SI 单位、插值、FK 一致性和无突跳。
