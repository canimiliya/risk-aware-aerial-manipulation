# S1-R1-R7 GPU 平行重建与 write 优先验收报告

## 结论

GPU 独立工作区已经按固定官方源码完成 19/19 Catkin 构建，GPU 环境本身也能运行 Torch 2.7.1+cu128 和 RTX 5060 Ti CUDA kernel。但构建出的 `se3_node` 同时链接 Python 3.8 和 Python 3.9；实际启动 write 时在 Python codec 初始化阶段退出，因此没有进入模型初始化、GPU 推理或轨迹优化。这个任务不算通过。

## 当前做到的

- 保留了 CPU 工作区、CPU 环境和 CPU `se3_node` 的前后基线；Conda explicit、pip freeze、源码 commit、CPU `se3_node` SHA 均未变。源文件清单的共同项逐项一致；前后差异只有 Catkin 产生的顶层 symlink 记录，已单独标注。
- 在独立 `/home/amplanner/am-planner-gpu-ws` 中使用官方固定 commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`，源码工作树干净，无 CPU 权重挂载。
- GPU 环境为 Python 3.9.23、Torch 2.7.1+cu128、CUDA 12.8、RTX 5060 Ti capability `(12, 0)`；`pip check` 通过。
- 经过依赖补齐后 Catkin 构建结果为 `All 19 packages succeeded!`。
- CMake 配置日志明确找到 GPU Conda 的 Python 3.9.23、头文件和 `libpython3.9.so`；运行时 `ldd` 的动态库已能解析。
- write 运行证据完整保留了原始失败和第 11 次隔离包装重试；第 11 次仍报 `failed to get the Python codec of the filesystem encoding`，随后 `se3_node` 以退出码 -6 结束。

## 还缺什么

- `se3_node` 的 Python ABI 仍不干净：ELF `NEEDED` 同时包含 `libpython3.8.so.1.0` 和 `libpython3.9.so.1.0`。这不是合格的“只链接 Python 3.9”结果。
- write 没有产生有效的 `/trajectory` 或 `/trajectory_arm`，也没有 `Using device: cuda`、JPS、MINCO 或 GPU 进程证据。
- 因为 write 未通过，按任务卡没有运行 grasp、lift，也没有运行 grasp 重复性验收。

## 是否通过

不通过。本轮完成了 GPU 工作区重建和失败诊断，但未完成 write 轨迹验收；不能把它写成三项官方轨迹复现通过。

## 是否需要我处理

需要你决定是否另行授权“处理 ROS Noetic 间接 Python 3.8 依赖并重新做 ABI/运行验证”。这会超出本轮“不改官方源码和参数”的边界；在得到新授权前，我不会继续修改源码、替换参数或运行 grasp/lift。

## 原始标签

`BLOCKED_S1_R1_GPU_PYTHON_ABI`：人话是“GPU 编译成功，但可执行文件混入 Python 3.8，write 启动不了，所以不能继续轨迹验收”。

低级提交状态保持 `S1-R1: SUBMITTED_FOR_REVIEW`（本轮证据已整理，等待你审阅），总阶段保持 `S1: IN_PROGRESS`（S1 尚未完成），`S2--S8: FROZEN`（后续阶段未开始）。

## Git 与证据

- 当前分支：`agent/s1-r1-am-planner-install-basic-repro`（仍在原工作分支）。
- 本轮开始时 Head：`6779657f0f0f9a6487204c4d8e362d6d5849bd8e`；PR #3 仍为 Open + Draft，未合并。
- 本轮最终 Head：`8dded82d6ea1589a5a1df748419014990a556cc8`（已推送到原分支；PR #3 仍保持 Draft）。
- GPU 构建、ABI 和 write 证据：`docs/evidence/S1-R1/gpu_rebuild/`。
- 第 11 次 write 失败运行：`docs/evidence/S1-R1/gpu_rebuild/write_gpu_run_01_retry_11/`。
- 自动审计：`docs/evidence/S1-R1/gpu_rebuild/gpu_rebuild_audit.json` 和 `gpu_rebuild_audit.md`。

## 检查结果

- `python -m compileall scripts`：通过。
- `git diff --check`：通过。
- 本轮专用 GPU 重建审计：2 个硬错误，正是 Python 3.8/3.9 混链和 write codec 启动失败；没有大文件或 wheel/CUDA/build 产物混入。
- 历史 S1 runtime、GPU 依赖恢复和 write 诊断审计保持原结论；基础 reproduction 审计仍因 write 双轨迹缺失而不通过，这是本轮要保留的事实。

## 明确未执行

未修改 CPU 环境；未修改官方 AM-Planner 源码、任务点、launch 或优化参数；未使用 CPU 权重替换；未下载新模型或 checkpoint；未运行 IL/Polynomial_DiT；未安装 Windows/WSL CUDA Toolkit；未执行 `wsl --shutdown`/注销；未 force-push、rebase、reset hard、合并 PR #3，也未进入 S2。
