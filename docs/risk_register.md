# 风险登记

| 风险 | 概率 | 影响 | 当前证据 | 触发条件 | 缓解措施 | 责任阶段 |
|---|---|---|---|---|---|---|
| RTX 50/Isaac 兼容性 | 中 | 高 | RTX 5060 Ti/driver 581.29 | 安装或启动失败 | 安装前核验，保留 headless 回退 | S3 |
| 16 GB 显存容量 | 中 | 高 | 16,311 MiB | OOM/吞吐不足 | 小并行、headless、D 盘缓存 | S3–S8 |
| C 盘容量与缓存 | 中 | 中 | 89.2 GB 可用 | 安装/缓存占满 | 优先规划 D 盘；不在 S0 改环境 | S1/S3 |
| Long Paths | 中 | 中 | LongPathsEnabled=0 | 深路径构建失败 | 只记录，不改注册表；阶段安装前评估 | S1 |
| Ubuntu 20.04/ROS Noetic | 高 | 高 | AirFAR-Ubuntu20 存在，os-release 探针超时 | AM-Planner 无法启动 | S1 只读复核或负责人批准新环境 | S1 |
| AM-Planner 依赖 | 中 | 高 | 未克隆，HEAD 已记录 | requirements/示例失败 | 冻结 commit、隔离安装 | S1 |
| Polynomial_DiT 无明确许可证 | 高 | 高 | 冻结 commit 无显式许可证 | 公开/再分发需求 | 不克隆、不再分发，先澄清 | S1 |
| Delta 臂进入 PhysX | 中 | 高 | 尚未验证 | 工作空间/闭链失败 | G-ARM 门槛与单元测试 | S2/G-BRIDGE |
| AM-Planner/Isaac 模型一致性 | 中 | 高 | 仅离线协议草案 | FK/关节/坐标不一致 | G-BRIDGE 校验器 | G-BRIDGE |
| 接触数值稳定性 | 中 | 高 | 未建模 | 时间步/求解器敏感 | 解析测试、合法接触分离统计 | S5 |
| 项目范围膨胀 | 中 | 高 | 当前仅 S0 | 加入视觉/真机/SLAM | 阶段冻结和负责人批准 | 全阶段 |
