# S0-R1-R1 返修报告

正式状态：`SUBMITTED_FOR_REVIEW`。本轮没有批准 S0，也没有进入 S1。

## 对第一次审查的响应

| 旧问题 | 本轮修复 |
|---|---|
| v1.2 被缩减 | 以归档 v1.0 为主体重建完整根目录 v1.2，补入当前事实、历史、硬件登记和返修状态 |
| 任务卡不完整 | 从本轮可读取的原始附件恢复 S0-R1 卡，并保存 S0-R1-R1 卡；规范化当前为 1003 行/26125 字节、SHA-256 `35454CA1AAAC783E9C4F6FA0DF6E5E2105675BACA7ED6CA629A02B6536D916FE`，与附件声明的 1056 行/27587 字节基准不一致，已由检查器警告而未伪造 |
| 工具链矛盾 | 新采集器真实运行版本命令，保存 status/path/version_output/exit_code、原始日志和 nvidia-smi 摘要 |
| WSL 编码损坏 | 新证据为 UTF-8 无 NUL；保留旧损坏证据；WSL 状态/版本和 AirFAR os-release 探针超时如实记录，发行版列表从旧原始输出解码保存 |
| 自动检查过弱 | 检查器现在检查路径、远程、分支、完整治理文件、JSON、版本文本、compute capability 分离、UTF-8/NUL、大文件和凭据模式 |
| 许可证审计不完整 | 保存 Isaac Lab v2.3.2 LICENSE 原文；AM-Planner 与 Polynomial_DiT 在冻结 commit 的无明确许可证状态分别记录 |

## 新证据结论

Windows 11 build 26100；Intel Core Ultra 7 270K Plus，24/24；RAM 50,873,458,688 bytes；RTX 5060 Ti 16,311 MiB，driver 581.29，compute capability 12.0；nvidia-smi 顶部驱动 CUDA Version 为 13.0；本地 CUDA Toolkit 为 `NOT_INSTALLED`。Python 3.13.9、Conda 26.1.1、Git 2.55.0、gh 2.96.0 均由真实版本命令记录；CMake/Ninja/Docker 为 `NOT_INSTALLED`。

候选硬件判断为 `HARDWARE_PASS_WITH_LIMITATIONS`，不是 S0 正式状态。环境仍是两套隔离的 `NOT_INSTALLED` 候选环境。

## 仍未验证/未安装

AirFAR-Ubuntu20 的 `/etc/os-release` 探针受控超时，不能声称 Ubuntu 20.04 或 ROS Noetic 就绪；AM-Planner、Polynomial_DiT、Isaac Sim/Lab、CUDA Toolkit 均未安装；没有训练、规划复现或正式实验。
