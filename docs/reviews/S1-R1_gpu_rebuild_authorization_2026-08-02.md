# S1-R1-R7 GPU 平行重建授权记录

日期：2026-08-02

审查 Head：`6779657f0f0f9a6487204c4d8e362d6d5849bd8e`

本轮授权依据：

- GPU 官方依赖恢复已完成；21/21 wheel 校验通过，离线安装后 `pip check=0`。
- RTX 5060 Ti 的 CUDA kernel、原始权重加载、WorkspaceMLP strict load/forward/autograd 均通过。
- batch 576/960 的 forward+autograd GPU 加速达到任务卡门槛，原始判断为 `GPU_REBUILD_RECOMMENDED`（人话：GPU 值得进入下一轮重建）。

本轮授权范围：

- 建立独立的 Python 3.9 + Torch 2.7.1 cu128 GPU Catkin 工作区 `/home/amplanner/am-planner-gpu-ws`。
- CPU 环境 `am-planner-py38` 和 CPU 工作区 `/home/amplanner/am-planner-ws` 必须保持不变。
- 优先验收 `write`；只有 write 通过后才允许运行 `grasp`、`lift` 和 grasp 重复性。
- 不修改 AM-Planner 官方源码、任务点、约束、launch 或优化参数。
- 不安装 torchvision/torchaudio、系统 CUDA Toolkit，不运行 IL/Polynomial_DiT，不进入 S2，不合并 PR #3。

审查结论：已授权按 S1-R1-R7 任务卡执行；若开始门槛、构建、Python ABI 或 GPU 实际使用证据不成立，应停止并按任务卡原始标签报告。
