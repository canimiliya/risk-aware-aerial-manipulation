# S0 最终高级总控审查

- 审查对象：S0-R1-R2
- 审查 Head：`2f441c4d4ebace01c3ef76cec00d546813dee267`
- 审查结论：`PASS_WITH_LIMITATIONS`
- S0 阶段结论：`PASS_WITH_LIMITATIONS`

## 已通过

1. 独立 Git 工作区和 GitHub 事实源建立；
2. 硬件、驱动、磁盘和工具链审计；
3. AM-Planner 与 Isaac Lab 环境隔离合同；
4. 第三方 commit 与许可证风险记录；
5. 权威任务卡、报告和证据链恢复；
6. 自动检查 `errors=0, warnings=0`；
7. 中断文件无损备份和一致性重建。

## 限制

1. Isaac Sim/Lab 未安装和启动；
2. WSL、Ubuntu 20.04、ROS Noetic 仍需 S1 预检；
3. LongPathsEnabled=0；
4. 16 GB 显存需要后续 headless/小并行实测；
5. AM-Planner、ROS、CUDA Toolkit、Polynomial_DiT 未安装；
6. Polynomial_DiT 无明确许可证，禁止公开再分发。

## 权限

- 允许完成 S0 状态收口并合并 PR #1；
- 合并后允许进入 S1 只读预检；
- 不允许直接安装或执行 AM-Planner；
- 不允许长训练。
