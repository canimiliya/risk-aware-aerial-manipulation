# S1-R1 write 长时间优化诊断报告（2026-07-31）

## 结论

write 没有崩，但在任务卡规定的 1200 秒内仍没有发布 `/trajectory` 和 `/trajectory_arm`。进程一直高负载运行，日志和 cost 持续更新，cost 从 `6.20901e17` 降到约 `1.49556e7`，因此不是“卡死”或新的明确运行错误，而是 CPU 太慢，优化在时限内算不完。

这不算三项轨迹验收通过：grasp/lift 保持已通过，write 仍未通过。本轮没有运行 grasp/lift，也没有改官方源码、任务点、参数或权重。

## 当前做到的

- 只读比较官方 grasp/lift/write 配置：write 有 6 个中间点，lift 有 1 个，grasp 为直接起终点；write 起终点距离更长，约束标志更密集。
- write 官方配置为 `Rho=0.001`、`TotalT=20`、`QdIntervals=96`、`MultiLayerOpt=false`、`OptRelTol1=1e-8`、`OptRelTol2=1e-10`；grasp/lift 的 `Rho=500`、`MultiLayerOpt=true`、收敛阈值更宽。
- 只读查清优化器：L-BFGS `past=3`，梯度阈值 `1e-32`，最大迭代次数未设置上限，write 关闭第二阶段；只有整个 MINCO 返回后才发布两条轨迹。
- 既有 300 秒日志显示 write 已完成 JPS、CPU 模型初始化和 MINCO setup，cost 持续变化但无完成日志。
- 正式受控运行一次，最长 1200 秒；60/300/600/900/1200 秒快照全部保存。
- CPU 峰值约 1937%，RSS 峰值约 689736 KB，监控采样 240 次，cost 样本约 7289；JPS 7 段，JPS 用时约 1.502 秒；双轨迹均未收到。
- CPU workspace 模型微基准已完成（Torch 2.4.1+cpu，24 线程，batch 1/96/192/576/960，forward 与 forward+autograd 各预热20次、正式100次）。

## 还缺什么

- write 的双轨迹仍未完成，因此没有进行 grasp 重复性，也没有进入 S2。
- 这轮只能确认 CPU 持续计算且太慢，不能证明更快硬件一定收敛；若要进一步诊断或改参数，需要新的明确授权。

## 是否算通过

不算 write 通过，也不算三项基础复现全通过；本轮“诊断证据完整”通过，write 结果属于 CPU 太慢。

## 下一步需要决定什么

你只需要决定是否授权下一轮对 write 进行新的受控方案（例如换硬件/参数或更深入的只读性能定位）。在你授权前，我不会改官方源码或参数，也不会运行其他任务。

## 原始标签

`SUBMITTED_S1_R1_WRITE_RUNTIME_TOO_SLOW`：意思是“write 在 1200 秒内没跑完，但证据显示程序一直活跃计算，判断为 CPU 太慢”；不是 write 已通过。

## GitHub 与现场

- 分支：`agent/s1-r1-am-planner-install-basic-repro`（本轮工作所在分支）。
- 起始 Head：`a6e5c69c5e53f7fac7af0d0d51244c9aa6f886da`（R4 已提交的现场）。
- PR #3：Open + Draft，未合并。
- S1：`IN_PROGRESS`；S2–S8：`FROZEN`。

## 关键证据

- `docs/evidence/S1-R1/write_diagnosis/task_complexity_comparison.json` / `.md`
- `docs/evidence/S1-R1/write_diagnosis/optimizer_static_contract.md`
- `docs/evidence/S1-R1/write_diagnosis/existing_log_comparison.json` / `.md`
- `docs/evidence/S1-R1/write_diagnosis/workspace_model_cpu_benchmark.json` / `.md`
- `docs/evidence/S1-R1/write_diagnosis/write_classification.json` / `.md`
- `docs/evidence/S1-R1/write_diagnosis_run_01/`（正式 1200 秒运行、监控、五个快照、清理记录）
