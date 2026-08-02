# S1-R1-R6-R1 官方 CUDA 依赖恢复与完整 GPU 预检报告（2026-07-31）

## 结论

官方 CUDA 运行库已经恢复并离线安装成功，RTX 5060 Ti 的真实 CUDA kernel、原始权重、WorkspaceMLP 模型和 CPU/GPU 微基准全部通过。本轮结论是：GPU 路线值得进入下一轮 AM-Planner 并行重建，但本轮没有重建 AM-Planner，也没有运行 grasp/write/lift。

## 当前做到的

- 从已安装 `torch 2.7.1+cu128` 的 `METADATA` 提取出 21 个 Linux/Python 3.9 依赖；锁 SHA-256：`cb4015bd905338be5cdd0606e935d1c239e5e213bad46ae631673f45ba841f55`。
- 21/21 个官方 wheel 通过 URL、字节数、SHA-256 和 ZIP 完整性校验；来源只来自 PyTorch/PyPI 官方域名。
- 独立环境 `am-planner-gpu-probe-py39` 离线安装完成，`pip check` 为 0；没有安装 torchvision 或 torchaudio。
- Torch/RTX 硬门槛通过：`2.7.1+cu128`、CUDA 12.8、`NVIDIA GeForce RTX 5060 Ti`、capability `(12,0)`、`sm_120`；CUDA tensor、1024×1024 matmul、Linear 和 autograd 全成功，无 unsupported architecture/no kernel image。
- 原始 `workspace_probability_weight.pth` 在 CUDA 上三种加载方式均成功；WorkspaceMLP `strict=True`、float32 forward 和 autograd 均成功，参数量 58,113。
- CPU/GPU WorkspaceMLP 微基准完成：batch 576 forward+autograd 中位数加速 `178.90x`，batch 960 为 `5.87x`，均超过 3x 门槛。
- CPU 环境清单 SHA 与 R6 前保持一致：`3BA72ABD182A6BACB66153C76C3402C139A8E5B1D118F5EEC2801EAA59A7E65E`；CPU Torch 仍为 `2.4.1+cpu`、CUDA=False；官方 AM-Planner 源码仍为固定 commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d` 且干净。

## 还缺什么

- 完整 AM-Planner 的 GPU 重建、GPU write/grasp/lift 运行证据还没有做；这不是本轮任务范围内的遗漏，而是下一轮授权项。
- 微基准只证明 WorkspaceMLP 这段计算值得上 GPU，不能替代 AM-Planner 的端到端 write 验收。
- 模型探针和微基准 stderr 记录了 Torch 因 GPU 环境没有 NumPy 而发出的提示；它不影响本轮 CUDA/模型门槛，且没有把 NumPy 额外装进锁定依赖。

## 是否算通过

算通过“官方 CUDA 依赖恢复与完整 GPU 预检”。不代表 write 或三项官方轨迹已经通过。

## 是否需要用户处理

需要你决定是否授权下一轮“GPU 路线 AM-Planner 并行重建”。在你授权前，我不会自动修改 AM-Planner、参数或运行 grasp/write/lift。

## 原始标签

`GPU_REBUILD_RECOMMENDED`：人话是“GPU 已经被实测证明可用，而且这段模型计算有明显加速，值得进入下一轮重建”；不是“AM-Planner 已重建完成”，也不是“write 已通过”。

## 关键证据

- `docs/evidence/S1-R1/gpu_dependency_recovery/gpu_runtime_lock.txt`
- `docs/evidence/S1-R1/gpu_dependency_recovery/official_wheel_manifest.json`
- `docs/evidence/S1-R1/gpu_dependency_recovery/wheelhouse_verification.md`
- `docs/evidence/S1-R1/gpu_dependency_recovery/gpu_torch_probe.json`
- `docs/evidence/S1-R1/gpu_dependency_recovery/gpu_checkpoint_probe.json`
- `docs/evidence/S1-R1/gpu_dependency_recovery/workspace_model_gpu_benchmark.json`
- `docs/evidence/S1-R1/gpu_dependency_recovery/cpu_gpu_benchmark_comparison.json`
- `docs/evidence/S1-R1/gpu_dependency_recovery/gpu_dependency_recovery_audit.json`
