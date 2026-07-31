# S1-R1 Torch 运行依赖审查

- 审查 Head：`9aed51801a61c012a1f13894b1dd021a3c93a7ea`
- 现有成果：隔离环境完成，AM-Planner 19/19 包构建成功。
- 运行阻塞：官方 `se3_node` 在基础规划中直接导入 `torch`。
- 源码证据：`WorkspaceProbabilityModel` 使用 `torch.nn`、`torch.load` 和 `torch.autograd`。
- 权重来源：AM-Planner 仓库自带 `traj_opt/weights/workspace_probability_weight.pth`。
- 设备策略：`torch.cuda.is_available()` 为假时自动使用 CPU。
- 本轮授权：只安装官方 CPU 版 `torch==2.4.1`。
- 继续禁止：`torchvision`、`torchaudio`、`triton`、Polynomial_DiT、IL 和 CUDA Toolkit。
