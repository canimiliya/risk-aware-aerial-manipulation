# GPU 路线判断

结论：`GPU_REBUILD_RECOMMENDED`。

人话：RTX 5060 Ti 的官方 CUDA 运行链已经真实跑通，原始权重和 WorkspaceMLP 也能在 GPU 上严格加载、前向和反向；在相同的 WorkspaceMLP 微基准中，batch 576 的 forward+autograd 中位数加速约 178.90 倍，batch 960 约 5.87 倍，超过任务卡的 3 倍门槛。因此，下一轮“并行重建 AM-Planner”值得做，但不由本轮自动开始。

这不等于 AM-Planner 的 write 已通过。完整 AM-Planner 重建、grasp/write/lift 和源码/参数修改都明确留到后续授权。
