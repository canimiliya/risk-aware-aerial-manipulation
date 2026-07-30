# 空中机械臂驱鸟器仿真研究项目

Repository: `risk-aware-aerial-manipulation`.

本项目研究风扰与接触不确定性下空中机械臂的风险感知全身轨迹执行。主链路为：AM-Planner 生成名义全身轨迹，离线轨迹文件经校验后由 Isaac Lab 执行控制与学习。

当前仅处于 **S0：初始化与硬件/依赖审计**。AM-Planner、Polynomial_DiT、Isaac Sim 与 Isaac Lab 均未安装；尚未复现算法、开始训练或产生实验结果。

协作采用 GitHub 审查：`main` 仅保存审查通过的内容；本次执行位于 `agent/s0-r1-workspace-hardware-audit`，等待高级总控审查后才可决定 S0 状态。

目录：`configs/` 配置草案，`planner_bridge/` 离线轨迹接口，`aerial_manipulation/` 仿真代码预留，`docs/` 治理与证据，`scripts/` 审计及后续入口，`tests/` 测试，`data/` 数据预留，`outputs/` 忽略的运行产物，`paper/` 论文材料。

后续顺序：S0 审查 → S1 AM-Planner 官方复现 → S2 工作空间可行性 → G-BRIDGE → Isaac Lab 与控制/实验阶段。未经阶段门槛通过，不得启动训练。

项目许可证：`PROJECT_LICENSE_DECISION_PENDING`；本仓库尚未选择许可证。
