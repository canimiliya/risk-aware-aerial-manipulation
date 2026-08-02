# S1-R1 状态
## R7 GPU 平行重建与 write 优先验收（2026-08-02）

- 已在独立 GPU Catkin 工作区用固定官方 commit 完成 19/19 构建，GPU 环境为 Python 3.9.23、Torch 2.7.1+cu128、RTX 5060 Ti，`pip check=0`。
- 构建出的 `se3_node` 同时链接 `libpython3.8.so.1.0` 和 `libpython3.9.so.1.0`；write 第 11 次隔离运行在 Python codec 初始化阶段退出，未发布轨迹。
- grasp、lift 和 grasp 重复性按门槛未运行；CPU 基线的 Conda、pip、源码 commit、CPU `se3_node` SHA 保持不变。
- 当前标签：`BLOCKED_S1_R1_GPU_PYTHON_ABI`（人话：GPU 编译成功，但 Python 版本混链导致 write 启动失败，不能继续三项轨迹验收）。
- 详细报告：`docs/reports/S1-R1_gpu_rebuild_and_runtime_report.md`。

## R6-R1 GPU 依赖恢复与完整预检（2026-07-31）

- 21/21 个官方 CUDA/PyTorch 运行库 wheel 已解析、下载、SHA/ZIP 校验并离线安装，`pip check=0`。
- RTX 5060 Ti / capability 12.0 / `sm_120` 的真实 CUDA tensor、matmul、Linear、autograd 通过；原始权重和 WorkspaceMLP strict forward/autograd 通过。
- WorkspaceMLP batch 576 / 960 的 forward+autograd 中位数分别达到 178.90x / 5.87x 加速。
- CPU 环境 SHA、CPU Torch、固定 AM-Planner 源码均未变化；没有重建 AM-Planner，也没有运行 grasp/write/lift。
- 当前 GPU 路线判断：`GPU_REBUILD_RECOMMENDED`（人话：值得授权下一轮并行重建，不是本轮已经重建完成）。
- 详细报告：`docs/reports/S1-R1_gpu_dependency_recovery_report.md`。

## 这次做到的

- 已在隔离的 `AMPlanner-Ubuntu20` 中复核：Python 3.8.20、autodiff 1.1.2、固定源码 commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。
- 使用系统 `/usr/bin/catkin` 增量构建，19/19 个包成功，退出码为 0；第三方源码保持干净。
- 已按本轮明确授权，从官方 CPU 索引安装 `torch==2.4.1+cpu`；`torch.nn` 和 autograd 自检成功，CUDA 为关闭状态。
- 仓库自带工作空间权重可在 CPU 上加载：10 个张量均为有限非零值。
- 安装后重新构建仍为 19/19 成功，固定第三方源码保持干净。
- 最小实验已证明 CPU 权重失败的根因：官方调用把 `map_location` 作为位置字典而不是关键字参数传入。CPU 规范化副本与原权重的 10 个张量逐项一致，模型严格加载、前向与梯度检查通过。
- 未改官方源码或原权重，使用临时 bind mount 覆盖运行时读取路径；退出后已卸载，官方原始 SHA 恢复，源码工作树干净。
- grasp 和 lift 都收到 `/trajectory` 与 `/trajectory_arm` 的真实非空消息；数值均有限且含非零数据。

## 还没有做到的

- write 在规定的 300 秒内没有发布两条轨迹；随后唯一一次最长 1200 秒诊断显示它一直高负载运行、cost 持续变化但仍未完成，分类为 `WRITE_CPU_RUNTIME_TOO_SLOW`（人话：CPU 太慢）。
- 三项未全过，因此未运行 grasp 重复性验收。

## 是否通过

不通过三项运行验收：grasp 与 lift 通过，write 未在 1200 秒内发布轨迹。CPU 权重反序列化问题已无源码修改地修复；R5 的 write 诊断已完成，后续如要继续需要新的授权。

## 原始标签

`SUBMITTED_S1_R1_WRITE_RUNTIME_TOO_SLOW`：意思是“write 在 1200 秒内没跑完，但程序一直活跃计算，判断为 CPU 太慢”；不表示 write 已通过。

S1 保持 `IN_PROGRESS`，S2--S8 保持 `FROZEN`；PR #3 保持 Draft，未合并。

## R6 GPU 独立预检（2026-07-31）

- WSL 已看到 RTX 5060 Ti / 驱动 581.29 / capability 12.0；官方 `torch-2.7.1+cu128` Python 3.9 wheel 已下载并完成 SHA 校验。
- 独立环境已建立，但 CUDA 运行库依赖没有在本轮网络窗口内完成安装，因此 kernel、原始权重、模型和 speedup 均未验证。
- CPU 环境前后清单 SHA 相同，Torch 仍为 `2.4.1+cpu`；官方源码仍固定且干净。
- GPU 预检标签：`REVISION_REQUIRED`（人话：硬件和 wheel 已确认，但关键运行证据还缺，不授权 GPU 重建）。详见 `docs/reports/S1-R1_gpu_preflight_report.md`。
