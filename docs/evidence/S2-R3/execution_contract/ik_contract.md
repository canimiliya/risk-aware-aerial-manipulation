# S2-R3 官方 IK/FK 合同

来源固定为 AM-Planner `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`，源码不复制入仓库；实际 `run_in_sim_grasp.launch` 参数为 `staticR=0.08`、`dynar=0.025`、`upper_arm=0.100`、`lower_arm=0.160`。

- `delta_display.cpp:353-398`：`endCallback` 接收 `/body/end_effector` 的 Cartesian point，按定义顺序 `x,y,z` 调用 `IK_kin`，检查有限性和 `[0, π/2]`，写入 `joint.position`，然后调用 `getJointPoints`。
- `delta_display.cpp:468-514`：官方 `IK_kin` 闭链解析式，输出三个主动关节角。
- `delta_display.cpp:516-564`：官方 `FK_kin` 闭链解析式。
- `delta_display.cpp:632-713`：官方 `getJointPoints` 输出 `A/B/C/B_left/B_right/C_left/C_right`。
- `delta_display.h:64` 的形参名为 `(y, x, z)`，而定义和 `endCallback` 使用 `(x, y, z)`；本项目通过 FK→IK 数值回环确认定义/调用顺序，未按头文件命名交换 x/y。

关节约定：`endCallback` 输出的 `q=[theta1,theta2,theta3]` 是 `[0,π/2]` 分支；`anglesCallback` 的 `FK_kin` 输入采用互补变量 `theta_fk=π/2-q`，再将 `joint.position=π/2-theta_fk`。项目 wrapper 同时保留 raw FK 和 joint-state FK，避免把两种约定混淆。
