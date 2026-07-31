# write 优化器停止条件与发布前置条件

来源是固定源码 commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d` 的只读检查；本轮没有修改官方源码。

## 关键位置

- `third_party/am-planner/src/plan/traj_opt/include/se3gcopter/lbfgs.h:57-102`：L-BFGS 参数含梯度阈值 `g_epsilon`、过去迭代间隔 `past`、相对变化阈值 `delta`、最大迭代次数 `max_iterations`、单轮最大 line-search 次数 `max_linesearch`。
- `third_party/am-planner/src/plan/traj_opt/include/se3gcopter/lbfgs.h:186-188`：默认值为 `g_epsilon=1e-5`、`past=0`、`delta=1e-5`、`max_iterations=0`（不设上限）、`max_linesearch=60`。
- `third_party/am-planner/src/plan/traj_opt/include/se3gcopter/lbfgs.h:1327-1329`：梯度归一化值达到 `g_epsilon` 时结束。
- `third_party/am-planner/src/plan/traj_opt/include/se3gcopter/lbfgs.h:1417-1430`：当 `past>0` 时，若过去 `past` 次的目标函数相对变化小于 `delta`，返回 `LBFGS_STOP`。
- `third_party/am-planner/src/plan/traj_opt/include/se3gcopter/lbfgs.h:1439-1443`：只有显式设置非零 `max_iterations` 才会因迭代上限结束；当前 AM-Planner 没有设置它。
- `third_party/am-planner/src/plan/traj_opt/include/se3gcopter/se3gcopter.h:1132-1138`：AM-Planner 实际把 `mem_size=128`、`past=3`、`min_step=1e-32`、`g_epsilon=1e-32`、`delta=OptRelTol1`、`line_search_type=0` 写入参数。
- `third_party/am-planner/src/plan/traj_opt/include/se3gcopter/se3gcopter.h:1144-1151`：先运行带约束的第一阶段 L-BFGS。
- `third_party/am-planner/src/plan/traj_opt/include/se3gcopter/se3gcopter.h:1162-1171`：仅当 `MultiLayerOpt=true` 才运行第二阶段；write 的官方配置为 `false`，因此 write 只有第一阶段。
- `third_party/am-planner/src/plan/traj_opt/src/se3_planner.cc:367-376`：`optimize()` 返回后才打印完成、耗时和最终 cost。
- `third_party/am-planner/src/plan/plan_manage/src/plan_manage.cpp:87-127`：只有 `plan()` 返回真，才构造轨迹消息并把 `traj_ready_` 置真。
- `third_party/am-planner/src/plan/plan_manage/src/plan_manage.cpp:243-250`：`traj_ready_` 为真后才发布 `/trajectory_arm` 和 `/trajectory`。

## write 的实际参数

- `OptRelTol1=1e-8`，`OptRelTol2=1e-10`；`Rho=0.001`；`TotalT=20`；`QdIntervals=96`；`MultiLayerOpt=false`。
- 因此“没有轨迹”不能解释为发布器先坏了：发布发生在整个 MINCO/L-BFGS 调用返回之后。1200 秒运行需要记录它是仍在求值、已停滞，还是出现错误。
