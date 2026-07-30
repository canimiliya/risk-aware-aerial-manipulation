# 硬件与系统审计

截图只作为线索；本页结论来自 `docs/evidence/S0-R1-R1/` 的命令证据。

| 项目 | 实测值 | 证据 |
|---|---|---|
| OS | Windows 11 build 26100, x64 | hardware_audit.json |
| CPU | Intel Core Ultra 7 270K Plus；24 核/24 逻辑线程 | hardware_audit.json |
| RAM | 50,873,458,688 bytes | hardware_audit.json |
| GPU/VRAM | RTX 5060 Ti / 16,311 MiB | nvidia_smi.txt |
| 驱动 | 581.29 | nvidia_smi.txt |
| GPU compute capability | 12.0 | hardware_audit.json（独立字段） |
| 驱动 CUDA 兼容值 | CUDA Version: 13.0（驱动报告的最高兼容 runtime 值） | nvidia_smi.txt |
| CUDA Toolkit | `NOT_INSTALLED`；nvcc 查询记录 | toolchain_raw.txt |
| 磁盘 | C: 214,754,652,160 总 / 89,245,347,840 剩余；D: 785,133,858,816 总 / 491,524,497,408 剩余 | path_and_disk_summary.txt |
| LongPathsEnabled | 0 | path_and_disk_summary.txt |
| WSL/发行版 | WSL2 可用；Ubuntu-24.04、Ubuntu、NMPC-Ubuntu22、dbLaCAM-Ubuntu、AirFAR-Ubuntu20；AirFAR `/etc/os-release` 探针超时 | wsl_*_utf8.txt |
| 工具链 | Python 3.13.9；Conda 26.1.1；Git 2.55.0；gh 2.96.0；CMake/Ninja/Docker 未安装 | toolchain_summary.txt |

候选判断：`HARDWARE_PASS_WITH_LIMITATIONS`，仅是执行 Agent 的候选判断。限制：Isaac Lab 未真实安装启动；16 GB 显存需要 headless/小并行；RTX 50 组合仍需实测；Long Paths 未启用；AM-Planner/ROS 未安装；C 盘不适合大型缓存，优先 D 盘规划，但本轮未改环境。
