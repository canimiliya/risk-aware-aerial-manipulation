# S1-R1 状态

## 这次做到的

- 已在隔离的 `AMPlanner-Ubuntu20` 中复核：Python 3.8.20、autodiff 1.1.2、固定源码 commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。
- 使用系统 `/usr/bin/catkin` 增量构建，19/19 个包成功，退出码为 0；第三方源码保持干净。
- 已按本轮明确授权，从官方 CPU 索引安装 `torch==2.4.1+cpu`；`torch.nn` 和 autograd 自检成功，CUDA 为关闭状态。
- 仓库自带工作空间权重可在 CPU 上加载：10 个张量均为有限非零值。
- 安装后重新构建仍为 19/19 成功，固定第三方源码保持干净。
- 最小实验已证明 CPU 权重失败的根因：官方调用把 `map_location` 作为位置字典而不是关键字参数传入。CPU 规范化副本与原权重的 10 个张量逐项一致，模型严格加载、前向与梯度检查通过。
- 未改官方源码或原权重，使用临时 bind mount 覆盖运行时读取路径；退出后已卸载，官方原始 SHA 恢复，源码工作树干净。
- grasp 和 lift 都收到 `/trajectory` 与 `/trajectory_arm` 的真实非空消息；数值均有限且含非零数据。

## 还没有做到的

- write 在规定的 300 秒内没有发布两条轨迹；随后唯一一次最长 1200 秒诊断显示它一直高负载运行、cost 持续变化但仍未完成，分类为 `WRITE_CPU_RUNTIME_TOO_SLOW`（人话：CPU 太慢）。
- 三项未全过，因此未运行 grasp 重复性验收。

## 是否通过

不通过三项运行验收：grasp 与 lift 通过，write 未在 1200 秒内发布轨迹。CPU 权重反序列化问题已无源码修改地修复；R5 的 write 诊断已完成，后续如要继续需要新的授权。

## 原始标签

`SUBMITTED_S1_R1_WRITE_RUNTIME_TOO_SLOW`：意思是“write 在 1200 秒内没跑完，但程序一直活跃计算，判断为 CPU 太慢”；不表示 write 已通过。

S1 保持 `IN_PROGRESS`，S2--S8 保持 `FROZEN`；PR #3 保持 Draft，未合并。
