# 环境隔离合同

| 环境 | 候选 OS/版本 | 用途 | 当前真实状态 | S1 候选 |
|---|---|---|---|---|
| AM-Planner | WSL2 Ubuntu 20.04，ROS Noetic，Python 3.8，Catkin | 官方示例、名义规划、离线轨迹导出 | `NOT_INSTALLED`；AirFAR-Ubuntu20 存在但 `/etc/os-release` 探针超时，ROS 未验证 | `FEASIBLE_WITH_LIMITATIONS`，需 S1 重新核验 |
| Isaac Lab | Windows 11，Isaac Sim 5.1，Isaac Lab v2.3.2，Python 3.11 | 动力学、接触、风扰、闭环与学习 | `NOT_INSTALLED` | `FEASIBLE_WITH_LIMITATIONS`，需安装批准和 RTX 50 实测 |

两套环境严格隔离，不共用 Conda，不建立实时 ROS 桥。唯一正式接口为离线轨迹文件与校验器。本轮未创建大型环境；候选方案不是已运行环境。
