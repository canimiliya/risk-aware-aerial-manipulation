# S2-R2 状态：BLOCKED_S2_R2_PLANNER_CONTRACT

## 结论

S2-R2 未进入真实运行。官方源码合同审计确认，`plan_manage` 可以读取 base 起止位置和中间点/方向约束，但不能表达“动态 base position + Delta 三关节 q + inter-points”的联合任务输入。任务卡要求在此条件下停止，不能自定义字段或把 S2-R1 插值结果伪装成 AM-Planner 输入。

## 先决环境

Python 3.9.23、Torch 2.7.1+cu128、CUDA/RTX 5060 Ti 和既有 ROS Python 3.9 overlay 已核验。全新 S2-R2 WSL clone 由于两次官方 GitHub 连接失败未能建立，因此没有声称新的 19/19 构建或 ABI 闭包。

## 当前状态

- S2-R0：`PASS_WITH_LIMITATIONS`。
- S2-R1：`PASS_WITH_LIMITATIONS`，范围是 fixed-WB continuous kinematic preplanning。
- S2-R2：`BLOCKED_S2_R2_PLANNER_CONTRACT`。
- S2：`IN_PROGRESS`；S3–S8：`FROZEN`。

## 未执行

未启动 S2-R2 `se3_node`、地图发布、接口冒烟、loose/nominal/repeat/narrow 运行、ROS 双轨迹捕获、连续重采样、动态 base 构造、可视化或真实轨迹导出。
