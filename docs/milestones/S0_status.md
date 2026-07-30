# S0 status

- S0-R1：`REVISION_REQUIRED`。
- S0-R1-R1：`REVISION_REQUIRED`。
- S0-R1-R2：`PASS_WITH_LIMITATIONS`。
- S0 正式阶段状态：`PASS_WITH_LIMITATIONS`。
- 批准审查 Head：`2f441c4d4ebace01c3ef76cec00d546813dee267`。
- S1：等待 PR #1 合并后进入只读预检；S1–S8：`FROZEN`；长训练：禁止。
- 已知限制：Isaac Sim/Lab、AM-Planner、ROS、CUDA Toolkit 未安装；AirFAR-Ubuntu20 系统版本 `NOT_VERIFIED`；LongPathsEnabled=0；16 GB 显存需后续 headless/小并行实测；Polynomial_DiT 无明确许可证，禁止公开再分发。
