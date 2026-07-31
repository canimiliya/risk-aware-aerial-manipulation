# S1-R1 write 长时间诊断审查记录（2026-07-31）

## 当前已知事实

- grasp 和 lift 已经有双轨迹、有限数值、非零数值的成功证据。
- write 的前一轮 300 秒运行没有发布 `/trajectory` 或 `/trajectory_arm`。
- 前一轮 write 没有发现 abort、segmentation fault 或 CPU 权重反序列化错误。
- write 日志显示 JPS 成功、CPU workspace 模型初始化成功、MINCO setup 成功，且 cost 在持续输出和变化。
- 现有证据尚不能把“CPU 太慢”和“优化停滞”区分开。

## 本轮边界

本轮只分析 write：比较官方任务复杂度，读取优化器停止条件，解析既有日志，建立低干扰监控，并执行一次最长 1200 秒的受控 write。不得运行 grasp/lift，不修改 AM-Planner 官方源码、tasks.yaml、任务点、launch 或优化参数，不使用重型 profiler。

## 本轮结论

1200 秒受控运行未产生 `/trajectory` 或 `/trajectory_arm`。`se3_node` 全程高负载运行，RSS 峰值约 689736 KB，cost 从 `6.20901e17` 降到约 `1.49556e7`，监控记录 7289 个 cost 样本，五个时间快照齐全；没有 abort、segmentation fault、NaN 或 Inf。按任务卡定义，本轮分类为 `WRITE_CPU_RUNTIME_TOO_SLOW`：人话是“程序一直在算，但 CPU 太慢，1200 秒仍算不完”。

监控器的 ROS 话题查询在启动时未继承 ROS PATH，少数 `topics` 字段记录为 command error；这条缺陷已如实保留，不影响运行器的 `rostopic_list`、捕获结果和其余 `/proc` 采样证据。
