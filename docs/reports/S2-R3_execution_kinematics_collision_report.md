# S2-R3 官方执行层关节/姿态/全身代理碰撞报告

## 结论

本轮完成了官方源码合同审计、项目自有 IK/FK/FlatnessMap wrapper、S2-R2 五组真实轨迹的 100/200/400/800 Hz 回放、全身代理几何、频率收敛、半径敏感性、重复性和 0.5 mm 自适应细分。真实判定为：

```text
S2-R3：SUBMITTED_S2_R3_IK_FAILED
review_state：SUBMITTED_FOR_REVIEW
S2：IN_PROGRESS
S3–S8：FROZEN
```

失败不是工具崩溃：官方 IK 对五组轨迹抽样和连续回放均产生有限输出且 FK 回环通过，但真实 `q(t)` 越过官方 `[0,π/2]` 执行分支；同时 body `0.20 m` provisional proxy 在 loose/nominal/repeat/narrow 全身 gate 下发生负 clearance。没有修改轨迹、缩小代理或降低 `0.010 m` gate。

## 官方合同与交叉验证

- 固定官方 commit：`7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。
- `delta_display.cpp:353-398`：`endCallback` 按 `x,y,z` 调用 `IK_kin`，检查 `[0,π/2]`，写入 `joint_states`，调用 `getJointPoints`。
- `delta_display.cpp:468-564`：官方 IK/FK；`632-713`：官方 joint points。
- `flatness.h:34-135` 和 `delta_display.cpp:205-252`：官方 FlatnessMap 执行层姿态映射。
- `traj_server.cpp:450-590`：官方五阶归一化多项式回放；`698-839`：两条 PolynomialTrajectory 输入合同。
- Python wrapper 与官方解析式逐项对应；1000 随机有效点、8 个边界候选、P0–P6 七个代表性候选点和五组各 100 点的 FK/IK 数值回环通过。raw FK 与 endCallback joint-state FK 的 `π/2-q` 互补约定已显式分离。

## IK/FK 和姿态结果

| 场景（800 Hz） | IK 无解 | max FK residual | min joint margin | joint limits |
|---|---:|---:|---:|---|
| smoke_free | 0 | 1.75e-16 m | -0.555228 rad | FAIL |
| loose | 0 | 1.75e-16 m | -0.365020 rad | FAIL |
| nominal | 0 | 1.75e-16 m | -0.216051 rad | FAIL |
| nominal repeat | 0 | 1.75e-16 m | -0.216051 rad | FAIL |
| narrow | 0 | 1.75e-16 m | -0.168218 rad | FAIL |

nominal FlatnessMap：quaternion finite，最大 norm error `2.22e-16`，最大正交误差 `3.85e-16`，`det(R)` 范围 `[0.9999999999999997,1.0000000000000002]`，thrust `[7.2477,14.9846] N`，max body omega `1.5500 rad/s`。这通过的是离线官方映射检查，不是闭环飞控。

## 全身代理碰撞

硬门槛组件共 16 个：body、4 rotor disks、3 upper-arm capsules、6 lower-rod capsules、moving platform、end-effector proxy。body/rotor 使用 `PROVISIONAL_S2_ASSUMPTION`，上/下臂中心线来自官方 `getJointPoints`，平台/EE 使用 `0.025 m` 任务代理。

| 场景（800 Hz） | min clearance | 最危险组件 | 时间 | 最近障碍点 | gate |
|---|---:|---|---:|---|---|
| loose | -0.095731 m | body | 4.20000 s | `[0.04,0.04,0.78]` | FAIL |
| nominal | -0.068486 m | body | 5.58375 s | `[-0.04,0.04,0.72]` | FAIL |
| nominal repeat | -0.068486 m | body | 5.58375 s | `[-0.04,0.04,0.72]` | FAIL |
| narrow | -0.103378 m | body | 4.94875 s | `[0.04,0.04,0.78]` | FAIL |

nominal 自适应细分使用 `0.0005 s` 步长，min-clearance 收敛差 `3.72e-7 m`，小于 `0.5 mm`。0.9/1.0/1.1 半径敏感性仍全部由 body 负 clearance 主导；没有用敏感性结果替换 nominal gate。

## 频率与重复性

100/200/400/800 Hz 均生成 joint trajectory、qdot/qddot、姿态和 16 组件碰撞结果。nominal/repeat 的 q 最大差异为 `0 rad`，min-clearance 差异为 `0 m`，最危险组件一致。频率结果在 `1e-5 m` 量级内稳定，不能改变 IK 或 body gate 的失败结论。

## ROS 回放与限制

本轮未重新启动 `traj_server`/`DeltaDisplay` live ROS 回放；保留了 `NOT_RUN_OFFLINE_VALIDATION_ONLY` 证据。原因是本轮使用已捕获的真实 S2-R2 原始 PolynomialTrajectory 做官方执行层离线重放，未安装新依赖或覆盖已验证 overlay。官方源码、已编译 `libdelta_display.so` 符号和源哈希已审计，但不把符号审计称为 live ROS 交叉回放。

本轮结果是 full-body proxy，不是 mesh 精确碰撞；qdot/qddot 是数值导数，不是执行器动力学；tool 完整长度/mesh 和 rotor 官方中心/半径仍不可得。
