# 硬件与系统审计

截图型号仅作线索；以下结论均来自 S0 命令采集的脱敏证据。Windows 11 build 26100，Intel Core Ultra 7 270K Plus（24 核/24 逻辑线程），RAM 50,873,458,688 bytes，RTX 5060 Ti（16,311 MiB，driver 581.29，compute capability 12.0）。C: 可用 89,245,347,840 bytes；D: 可用 491,524,497,408 bytes。

Isaac Lab 候选条件：GPU 与 16 GB VRAM 接近候选平台的容量门槛，可能需要 headless 和较小并行环境；RTX 50 系与驱动组合必须在获批安装后实测。当前无 CUDA Toolkit；这不等同于 GPU 或 Isaac Lab 不可用。WSL2 已启用，但未见 Ubuntu 20.04；ROS Noetic 环境未验证。完整字段见 `docs/evidence/S0-R1/hardware_audit.json`。
