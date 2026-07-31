# S1-R1 状态

## 这次做到的

- 已在隔离的 `AMPlanner-Ubuntu20` 中复核：Python 3.8.20、autodiff 1.1.2、固定源码 commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。
- 使用系统 `/usr/bin/catkin` 增量构建，19/19 个包成功，退出码为 0；第三方源码保持干净。
- 已建立独立 ROS 运行器和双话题消息捕获器；保留了三次 grasp 尝试的全部小型日志。
- 已查明运行阻塞：官方 `se3_node` 在路径搜索完成后强制导入 `torch` 的工作区概率模型；当前任务禁止安装 torch、torchvision、triton，也禁止改 AM-Planner 源码。

## 还没有做到的

- 没有得到 grasp、write、lift 的 `/trajectory` 和 `/trajectory_arm` 真实消息。
- 因为 grasp 在共同的 `se3_node` 运行时依赖处中止，未把 write/lift 伪装成可通过的独立任务，也没有进行 grasp 重复性验收。

## 是否通过

不通过运行验收，但构建成果已保护且可复现。需要上级明确允许一种后续路径：允许安装被禁止的运行依赖，或提供不依赖该模型的官方运行入口。

## 原始标签

`SUBMITTED_S1_R1_BUILD_WITH_RUNTIME_BLOCKER`：意思是“构建已经成功，但实际出轨迹被明确、可复现的运行时限制挡住”。

S1 保持 `IN_PROGRESS`，S2--S8 保持 `FROZEN`；PR #3 保持 Draft，未合并。
