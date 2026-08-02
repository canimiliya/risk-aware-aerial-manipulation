# S1-R1 安装、构建和基础运行报告
## R7 GPU 平行重建补充（2026-08-02）

GPU 独立工作区已用固定官方源码完成 19/19 构建，GPU Torch/RTX 预检和 `pip check` 通过；但 `se3_node` 的 ELF 依赖同时包含 Python 3.8 与 Python 3.9。write 第 11 次运行在 Python codec 初始化阶段失败，没有 `/trajectory`、`/trajectory_arm` 或 GPU 推理证据。因此本轮不通过，grasp/lift 及 grasp 重复性没有运行。详见 `docs/reports/S1-R1_gpu_rebuild_and_runtime_report.md` 和 `docs/evidence/S1-R1/gpu_rebuild/`。

## R6-R1 GPU 路线补充（2026-07-31）

官方 CUDA 依赖恢复和完整 GPU 预检已完成，结论为 `GPU_REBUILD_RECOMMENDED`：GPU 硬件、Torch cu128、真实 `sm_120` kernel、原始权重、WorkspaceMLP strict forward/autograd 和关键 batch 微基准均通过。

这个结论只授权“是否值得下一轮并行重建”的判断，不改变当前 CPU write 未通过的历史事实，也不表示本轮执行了 AM-Planner 重建或 grasp/write/lift。

证据目录：`docs/evidence/S1-R1/gpu_dependency_recovery/`；详细报告：`docs/reports/S1-R1_gpu_dependency_recovery_report.md`。

## 结论

官方 CPU Torch 已安装、仓库自带权重已验证可加载、19/19 构建仍成功。CPU 反序列化问题已在不改官方源码的条件下修复；grasp 与 lift 已产生真实双轨迹。R5 对 write 做了唯一一次最长 1200 秒诊断：它一直高负载计算、cost 持续变化但仍未发布轨迹，分类为 CPU 太慢；三项验收仍未通过。

## 当前做到的

- Miniforge 26.3.2-2、Python 3.8.20、autodiff 1.1.2 与官方 CPU `torch==2.4.1+cpu` 已保留在隔离发行版中；CUDA 未启用。
- AM-Planner 固定在 `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`，工作树干净。
- `/usr/bin/catkin` 的增量构建为 19/19 成功、退出码 0。此前 Conda 自带 catkin 的 `KeyError: _Context__extend_path` 没有再用；系统 catkin 负责构建，Conda 仅提供 Python/autodiff 的 CMake 前缀。
- 运行器为每次运行建立独立 ROS master、ROS_HOME、PID 和日志目录；捕获器在 launch 前启动，订阅 `/trajectory` 与 `/trajectory_arm`。
- `torch.nn`、autograd 和仓库自带工作空间权重均已独立验证；未安装 torchvision、torchaudio 或 triton。
- 最小复现实验证明位置字典调用稳定失败、关键字 `map_location="cpu"` 稳定成功。CPU 转换副本未提交 Git，并以临时 bind mount 供运行时读取；卸载后官方文件 SHA 恢复。
- grasp 与 lift 均捕获到两条真实轨迹，均无 NaN/Inf 且有非零数值；write 在 300 秒时限内未捕获轨迹。

## 还缺什么

- write 的两条非空轨迹消息与 grasp 重复性未完成；write 1200 秒诊断证据已完成，但 write 仍未通过。

## 是否需要我处理

需要你决定是否授权新的 write 性能定位或方案尝试；本轮没有修改 AM-Planner 源码，也不应把它写成三项基础复现通过。

## 证据

- Torch 与权重：`docs/evidence/S1-R1/torch_runtime/`
- 构建：`docs/evidence/S1-R1/build_after_torch/build_after_torch.log`
- CPU 权重修复：`docs/evidence/S1-R1/cpu_checkpoint_fix/`
- 基础运行与消息检查：`docs/evidence/S1-R1/runtime/grasp_cpu_checkpoint_run_02/`、`write_cpu_checkpoint_run_01/`、`lift_cpu_checkpoint_run_01/`
- write 1200 秒诊断：`docs/evidence/S1-R1/write_diagnosis/` 与 `docs/evidence/S1-R1/write_diagnosis_run_01/`

## 原始标签

`SUBMITTED_S1_R1_WRITE_RUNTIME_TOO_SLOW`：意思是“write 诊断证据完整，但 CPU 在 1200 秒内仍算不完；grasp/lift 已通过，write 未通过”。

## R6 GPU 独立预检补充

WSL GPU 直通和 RTX 5060 Ti 已确认，官方 PyTorch 2.7.1 cu128 wheel 已取得并校验；但 CUDA 运行库依赖未完成安装，所以没有 kernel、权重、模型或 CPU/GPU speedup 证据。状态保持 `REVISION_REQUIRED`，不能写成 GPU 路线通过，也没有重建或运行任何轨迹。详见 `docs/reports/S1-R1_gpu_preflight_report.md`。
