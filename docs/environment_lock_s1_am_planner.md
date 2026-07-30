# S1 AM-Planner 正式安装合同草案（未执行）

## 已验证事实

- 候选 `AirFAR-Ubuntu20` 为 Ubuntu 20.04.6，具备 `/opt/ros/noetic` 和 `ros-noetic-ros-base`，但属于既有 AirFAR 环境；本轮没有修改它。
- 推荐策略为 `CREATE_NEW_ISOLATED_UBUNTU20_RECOMMENDED`，避免污染既有项目。
- AM-Planner 固定 commit：`7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`；Polynomial_DiT 固定 commit：`f31c8f04e5fa045bc08c7bbaaadfe60bb54816f1`。

## 源码推断的下一轮安装合同

| 项目 | 草案（均待下一任务批准与实装验证） |
|---|---|
| WSL 发行版 | 新建、隔离的 `AMPlanner-Ubuntu20`；不得复用 AirFAR-Ubuntu20 |
| Ubuntu / ROS | Ubuntu 20.04 + ROS Noetic；安装方式待任务卡固定 |
| Python | Conda/Mamba 环境名 `am-planner-py38`，Python 3.8 |
| Catkin 工作区 | `~/am-planner-ws`，源码置于 `~/am-planner-ws/src/am-planner` |
| AM-Planner | 固定上述 commit；不得漂移 |
| APT 候选 | ROS Noetic 基础、`ros-noetic-octomap-ros`、`pybind11-dev`；其余按源码包清单核验 |
| Python 候选 | `requirements.txt` 固定包，以及 `autodiff`；不得在本轮安装 |
| CUDA | 基础规划不是当前源码确认的硬依赖；README 仅标为推荐。IL/torch 路径需后续单独实测 |
| Polynomial_DiT | 基础规划先绕过；如需 IL，先隔离源码和模型缓存，记录 Hugging Face 仓库、文件清单、许可证与哈希 |
| 第三方源码 | WSL 工作区内、项目 Git 忽略目录；不得提交到本项目 Git |
| 日志 | `~/am-planner-ws/logs` 与本项目 `docs/evidence/S1-R1/` 的命令/哈希证据 |
| 磁盘 | 安装前重新测量；预留至少 30 GB，模型大小本轮不可从源码可靠推断 |
| 失败回滚 | 仅删除下一轮新建的隔离发行版或工作区，须获得明确授权；绝不改动 AirFAR-Ubuntu20 |

## 下一轮待安装验证

ROS 包解析、APT/Python 精确依赖、catkin 构建、CUDA/torch 兼容性、模型文件大小及许可证、实际轨迹输出和官方示例均未验证。本草案不是安装完成声明。

