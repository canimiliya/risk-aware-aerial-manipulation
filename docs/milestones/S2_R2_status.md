# S2-R2 状态：SUBMITTED_FOR_REVIEW

## 结论

S2-R2 已按纠正后的官方 AM-Planner 合同完成工程验收，并提交复核；本文件不把它写成 S2 总体 PASS。旧的 `BLOCKED_S2_R2_PLANNER_CONTRACT` 是历史合同误判，原始失败运行和旧审计记录仍保留。

## 已完成

- 官方 commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d` 的干净 S2-R2 WSL workspace。
- 只应用已接受的两个 CMake ABI 修补，19/19 项目包构建成功；ABI runtime closure 和 RTX 5060 Ti CUDA 探针通过。
- 修正并冻结四种 `inter_info` 模式的机器合同：长度 `4/7/17/20`；mode 2 是位置、轴/开关、速度/开关和轴固定开关；没有 q[3] 任务字段。
- 真实 `se3_node`、点云地图和 mode-2 横担任务运行：smoke-free、loose、nominal、nominal repeat、narrow diagnostic 均捕获 `/trajectory` 与 `/trajectory_arm`，双轨迹有限且非空。
- nominal repeat 的合同、端点和 100/200/400 Hz 独立重采样比较一致。

## 边界与下一步

- `/trajectory_arm` 是 Cartesian polynomial trajectory，不是 Delta joint `q(t)`；本轮不虚构 IK 轨迹或关节限位通过。
- direction 采用官方 `se3_planner` JPS 日志与 mode-2 轴语义做等价水平约束验证：端点误差和水平段方向误差均为 0；连续 `PolynomialTrajectory` 工具轴误差仍因消息不携带原始 flag/vector 而不宣称可计算。
- S2 保持 `IN_PROGRESS`；S3-S8 保持 `FROZEN`。等待项目负责人对 S2-R2 提交复核后再决定是否推进。
