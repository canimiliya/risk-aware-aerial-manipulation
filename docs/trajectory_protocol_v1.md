# S3-R0 离线轨迹协议 v1

本协议把 S2-R6 已冻结的 `nominal_100w0` 与 `nominal_repeat_final_100w0` 两次 AM-Planner 输出转换为可重复的、与 ROS/Isaac 解耦的 reference-state playback 输入。协议不改写 S2 轨迹、barrier、anchor、权重或 tau。

每个 bundle 保存原始 `/trajectory` 与 `/trajectory_arm` 多项式、200 Hz canonical full-state、阶段标注和 SHA-256 manifest。base 与 arm 的多项式仍按 AM-Planner 的 descending-power、归一化段时间约定求值；速度、加速度和 jerk 由同一原始多项式求导。

字段使用 SI 单位：`time` 秒、位置米、速度米/秒、加速度米/秒²、jerk 米/秒³、关节角弧度。`q/qdot/qddot` 使用项目已有 Delta official IK 对 arm Cartesian reference 的确定性重建，FK residual 由回放审计重新计算；它们不是新的规划输出。

S3 场景合同暂定 A0 与 base reference origin 重合，world EE position = base position + A0 arm position。未从 Cartesian source 虚构完整末端 quaternion；工具方向字段固定为 `EQUIVALENT_HORIZONTAL_DIRECTION_CONSTRAINT`。

导出命令：

```powershell
python planner_bridge/protocol/export_s3_trajectory.py
```

输出位于 `data/trajectories/S3-R0/nominal_100w0` 与 `data/trajectories/S3-R0/nominal_repeat_100w0`。Isaac 阶段只读取这些离线 bundle，不建立 ROS/ROS2 实时桥。
