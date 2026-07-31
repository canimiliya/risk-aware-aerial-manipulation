# S1-R1 安装、构建和基础运行报告

## 结论

官方 CPU Torch 已安装、仓库自带权重已验证可加载、19/19 构建仍成功。CPU 反序列化问题已在不改官方源码的条件下修复；grasp 与 lift 已产生真实双轨迹，但 write 在 300 秒内未发布轨迹，因此三项验收未通过。

## 当前做到的

- Miniforge 26.3.2-2、Python 3.8.20、autodiff 1.1.2 与官方 CPU `torch==2.4.1+cpu` 已保留在隔离发行版中；CUDA 未启用。
- AM-Planner 固定在 `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`，工作树干净。
- `/usr/bin/catkin` 的增量构建为 19/19 成功、退出码 0。此前 Conda 自带 catkin 的 `KeyError: _Context__extend_path` 没有再用；系统 catkin 负责构建，Conda 仅提供 Python/autodiff 的 CMake 前缀。
- 运行器为每次运行建立独立 ROS master、ROS_HOME、PID 和日志目录；捕获器在 launch 前启动，订阅 `/trajectory` 与 `/trajectory_arm`。
- `torch.nn`、autograd 和仓库自带工作空间权重均已独立验证；未安装 torchvision、torchaudio 或 triton。
- 最小复现实验证明位置字典调用稳定失败、关键字 `map_location="cpu"` 稳定成功。CPU 转换副本未提交 Git，并以临时 bind mount 供运行时读取；卸载后官方文件 SHA 恢复。
- grasp 与 lift 均捕获到两条真实轨迹，均无 NaN/Inf 且有非零数值；write 在 300 秒时限内未捕获轨迹。

## 还缺什么

- write 的两条非空轨迹消息与 grasp 重复性未完成。

## 是否需要我处理

需要你决定是否授权下一轮仅诊断 write 未在 300 秒内发布轨迹的原因；本轮没有修改 AM-Planner 源码，也不应把它写成三项基础复现通过。

## 证据

- Torch 与权重：`docs/evidence/S1-R1/torch_runtime/`
- 构建：`docs/evidence/S1-R1/build_after_torch/build_after_torch.log`
- CPU 权重修复：`docs/evidence/S1-R1/cpu_checkpoint_fix/`
- 本轮运行与消息检查：`docs/evidence/S1-R1/runtime/grasp_cpu_checkpoint_run_02/`、`write_cpu_checkpoint_run_01/`、`lift_cpu_checkpoint_run_01/`

## 原始标签

`SUBMITTED_S1_R1_BUILD_WITH_RUNTIME_BLOCKER`：CPU 权重问题已解决、部分任务已运行成功，但 write 仍被运行时限内无轨迹这一问题拦住。
