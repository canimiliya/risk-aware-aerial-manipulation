# S1-R1 Torch 后运行阻塞证据

- 官方 CPU `torch==2.4.1+cpu` 已安装；`torch.nn`、autograd 与 CPU 模式均已自检通过。
- 仓库自带工作空间权重可加载：10 个张量均为有限且非零值。
- 构建门槛仍成功：`/usr/bin/catkin build --summarize --no-status` 显示 `All 19 packages succeeded`，退出码为 0。
- 固定第三方源码仍是 `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`，运行前后均未修改。
- 三次 Torch 后的 grasp 尝试均启动 `se3_node`，收到点云、完成 JPS，并进入 MINCO 初始化；随后官方节点 abort（退出码 -6）。
- 两条轨迹话题类型均已出现，但三次捕获器都没有收到 `/trajectory` 或 `/trajectory_arm` 的真实消息。
- 因 grasp 未完整通过，未运行 write、lift 或重复性；未安装 torchvision、torchaudio、triton，未下载 Polynomial_DiT/checkpoint，未运行 IL，未修改第三方源码、合并 PR 或进入 S2。
- 结论：运行仍被官方节点的 abort 挡住，不能写成三项基础轨迹复现成功。
