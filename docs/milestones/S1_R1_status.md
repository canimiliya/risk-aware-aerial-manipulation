# S1-R1 状态

## 这次做到的

- 已在隔离的 `AMPlanner-Ubuntu20` 中复核：Python 3.8.20、autodiff 1.1.2、固定源码 commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。
- 使用系统 `/usr/bin/catkin` 增量构建，19/19 个包成功，退出码为 0；第三方源码保持干净。
- 已按本轮明确授权，从官方 CPU 索引安装 `torch==2.4.1+cpu`；`torch.nn` 和 autograd 自检成功，CUDA 为关闭状态。
- 仓库自带工作空间权重可在 CPU 上加载：10 个张量均为有限非零值。
- 安装后重新构建仍为 19/19 成功，固定第三方源码保持干净。
- 已建立独立 ROS 运行器和双话题消息捕获器；保留了三次 Torch 后的 grasp 尝试及全部小型日志。

## 还没有做到的

- 没有得到 grasp、write、lift 的 `/trajectory` 和 `/trajectory_arm` 真实消息。
- 三次 grasp 都在点云、JPS 和 MINCO 初始化后由官方 `se3_node` 以 abort（退出码 -6）退出；两条话题虽已声明，但捕获器均未收到消息。
- 任务卡规定 grasp 未通过时停止，因此没有伪跑 write/lift，也没有进行 grasp 重复性验收。

## 是否通过

不通过三项运行验收，但 Torch、权重加载和构建均已通过。后续需要定位官方 `se3_node` 在 CPU Torch 已可用后的 abort 根因；本轮不得靠修改 AM-Planner 源码绕开它。

## 原始标签

`SUBMITTED_FOR_REVIEW`：意思是“本轮证据已提交等待审查”，不表示三项轨迹已经通过。此次提交的实际结果仍是“构建成功、grasp 因官方节点 abort 未出轨迹”。

S1 保持 `IN_PROGRESS`，S2--S8 保持 `FROZEN`；PR #3 保持 Draft，未合并。
