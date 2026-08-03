# S2-R2 AM-Planner 横担连续规划报告

## 结论

本轮停止于真实运行前的 planner-contract gate：`BLOCKED_S2_R2_PLANNER_CONTRACT`。

这不是 nominal 规划失败，也不是 clearance、kinematic 或 direction 失败；没有启动 `se3_node`，没有生成自有假轨迹，也没有捕获空的 ROS 消息来冒充结果。

## 证据摘要

- 固定官方来源：`7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。
- 官方模式 2 的 start/end 只填充 base `x,y,z`；源码行证据见 `docs/evidence/S2-R2/planner_contract/state_vector_contract.md`。
- `inter_points` 是无命名数值向量，接受长度 4/7/17/20；方向/平面约束只在 mode 2 的特定元素上生效。
- ROS 输出设计为 `/trajectory` 和 `/trajectory_arm` 两条 `PolynomialTrajectory`，但没有运行证据。
- 动态 base 与 Delta 三关节 q 的联合输入不在官方合同内。

## 环境失败证据

建立 `/home/amplanner/am-planner-s2-r2-ws` 的官方 clone 两次失败：第一次为 `GnuTLS recv error (-110)`，第二次为 GitHub 443 连接超时。旧工作区和旧 build/devel/install 未复用。

## 状态边界

S2 仍为 `IN_PROGRESS`，S3–S8 继续 `FROZEN`。要解除本阻断，需要项目负责人确认一个有官方源码依据的动态 base + Delta q 输入合同，或接受重新定义 S2-R2 的可验证目标；本轮不自行发明接口。
