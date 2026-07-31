# S1-R1 R6 RTX 5060 Ti GPU 路线独立预检报告（2026-07-31）

## 结论

本轮确认了硬件直通和官方 Torch wheel 可取得，但没有完成 CUDA 运行库依赖安装，因此没有完成 kernel、权重、模型和性能验证。状态是 `REVISION_REQUIRED`，不授权 GPU 重建，也不宣称 write 通过。

## 当前做到的

- WSL `AMPlanner-Ubuntu20` 可访问 `/dev/dxg`；`nvidia-smi` 看到 NVIDIA GeForce RTX 5060 Ti、驱动 581.29、16311 MiB、compute capability 12.0。
- 新建独立环境 `am-planner-gpu-probe-py39`，Python 3.9.23；没有改 `am-planner-py38`。
- 官方索引确认有 `torch 2.7.1+cu128`。wheel SHA-256 为 `738ac9b3ad79e62a21256e3d250cee858de955f93f89fab114da8d1919347d06`。
- Torch 本体已放入独立环境；其 nvidia-cu12 运行库依赖下载/安装未完成，故 Torch import 和 CUDA kernel 未执行。
- CPU 环境前后清单 SHA 相同：`3BA72ABD182A6BACB66153C76C3402C139A8E5B1D118F5EEC2801EAA59A7E65E`；CPU Torch 仍为 2.4.1+cpu、CUDA=False。
- 官方 AM-Planner 源码仍为 `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d` 且干净，无权重 bind mount。

## 还没做到的

- CUDA tensor、矩阵乘、nn、autograd 和 sm_120 kernel 未验证。
- 原始权重三种加载方式、strict load、GPU forward/autograd 未验证。
- CPU/GPU 模型微基准和 speedup 未产生。
- 因而不能回答 GPU 是否能显著加速 write，也不能判断是否值得平行重建。

## 明确未执行

未重建 AM-Planner，未运行 grasp/write/lift，未修改官方源码、任务点或参数，未安装系统 CUDA Toolkit，未运行 IL，未下载 Polynomial_DiT 或额外 checkpoint，未进入 S2，未合并 PR #3。

## 原始标签

`REVISION_REQUIRED`：不是“GPU 不行”，而是本轮依赖安装没有完成，关键证据还缺，必须另开授权窗口后才能继续判断。
