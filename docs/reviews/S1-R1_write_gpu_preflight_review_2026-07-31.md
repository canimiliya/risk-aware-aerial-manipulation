# S1-R1 R6 GPU 路线独立预检审查（2026-07-31）

## 本轮决定

- 审查起点 Head：`e8aea97347a78c9f0d22e58d5d51e42763055c7b`。
- write 已在 CPU 上受控运行 1200 秒，程序未崩溃、cost 持续变化，但没有发布两条轨迹；本轮不继续无限延长 CPU。
- 不授权修改官方参数、不授权修改官方源码、不授权重建 AM-Planner，也不运行 grasp/write/lift。
- RTX 5060 Ti（Blackwell，compute capability 12.0）作为独立路线预检对象。
- 当前 `am-planner-py38`（Python 3.8.20、Torch 2.4.1+cpu）保持不变；GPU 预检使用平行 Python 3.9 环境和官方 PyTorch 2.7.1 cu128。
- 本轮只建立 GPU 探针环境，验证 WSL 直通、Torch kernel、原始权重、模型 forward/autograd，并与现有 CPU 微基准对比；不据此宣称 write 或 S1-R1 通过。

## 范围边界

本文件记录高级总控决定。所有实际探针输出、环境清单、哈希和最终路线判断放在 `docs/evidence/S1-R1/gpu_preflight/`；若任一硬门槛失败，保留失败证据并停止在对应阻断标签。
