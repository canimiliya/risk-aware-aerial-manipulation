# 环境隔离合同

| 环境 | 候选位置 | 版本约束 | 用途 | S0 状态 |
|---|---|---|---|---|
| AM-Planner | WSL2 Ubuntu 20.04 或独立 Ubuntu 20.04 | ROS Noetic, Python 3.8, CUDA 11.8, Catkin | 官方示例、名义规划、离线轨迹导出 | `NOT_INSTALLED` |
| Isaac Lab | Windows 11 本机 | Isaac Sim 5.1, Isaac Lab v2.3.2, Python 3.11 | 动力学、接触、风扰、闭环控制与学习 | `NOT_INSTALLED` |

两者不得安装进同一 Conda 环境，不建立实时 ROS 桥。唯一正式接口是离线轨迹文件与校验器。根据 S0 实测，方案为 `FEASIBLE_WITH_LIMITATIONS`：WSL2 存在但无 Ubuntu 20.04，Windows GPU/驱动存在但 CUDA Toolkit、Isaac 平台均未安装；后续安装前必须重新审批。
