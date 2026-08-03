# S2-R3 失败证据接受审查

## 审查结论

```text
decision：FAILURE_EVIDENCE_ACCEPTED
S2-R3：FAILURE_EVIDENCE_ACCEPTED
S2：IN_PROGRESS
S3–S8：FROZEN
```

本审查接受 S2-R3 的失败证据，不把失败证据的审计通过误写为方法通过。独立复核确认：官方 Delta IK/FK 与 FlatnessMap 数值实现本身可回环，但当前 S2-R2 真实 `PolynomialTrajectory` 在官方 `DeltaDisplay::endCallback` 执行分支上越过 `q∈[0,π/2]`，并且 body `0.20 m` provisional proxy 的 nominal full-body clearance 为负。

## 独立复核

- 官方来源固定为 AM-Planner `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`；未修改官方 C++、URDF/Xacro、ROS 或环境。
- 复核了 nominal/nominal repeat/loose/narrow 的 100/200/400/800 Hz 离线官方执行层回放；结果与 S2-R3 原始证据一致。
- 1000 个随机有效点、8 个边界候选、P0–P6 代表点和五组各 100 点的 IK/FK 回环无 IK 无解；nominal 800 Hz max FK residual 为 `1.7507444764289613e-16 m`。
- nominal 800 Hz min joint margin 为 `-0.2160505211570365 rad`；nominal body min clearance 为 `-0.0684855999417475 m`，最危险组件为 body，时间 `5.58375 s`。
- nominal repeat 的 q 最大差异和 min-clearance 差异均为 `0`；100/200/400/800 Hz 频率收敛成立；body 自适应细分 `0.0005 s` 的收敛差为 `3.720927713168898e-07 m`。

## accepted findings

1. 官方 IK/FK 公式、joint convention 和 FlatnessMap wrapper 通过数值复核。
2. 当前真实 planner arm trajectory 离开官方执行关节分支；不存在 q clipping 或未经证明的分支替换。
3. 当前 nominal body proxy clearance 低于 `0.010 m` gate；未缩小 body/rotor/link proxy、未移动/缩小障碍、未降低 gate。
4. 两类失败相互独立，且在重复运行与采样频率变化下可复现。
5. 当前 S2 未就绪；下一轮仅允许 task-level execution-feasible constrained replan，不允许修改算法核心或直接进入 S3/Isaac Lab。

## 未解决限制

- body/rotor/link 为代理几何而非 mesh 精确碰撞；官方 rotor 中心/半径和完整 tool mesh 仍不可得。
- 本轮未重新启动 live `traj_server`/`DeltaDisplay` ROS 回放，保留 `NOT_RUN_OFFLINE_VALIDATION_ONLY`；原始 S2-R2 轨迹未被覆盖。
- qdot/qddot 为数值诊断，不等同于执行器动力学或飞控闭环可行性。

## 后续边界

PR #7 仅收口并接受失败证据。后续 S2-R4 必须从最新 `main` 创建独立 Draft PR，通过执行可行 arm envelope、安全 base corridor 和官方 mode 0/1/2/3 约束重规划；即使成功，也只能提交复核，不能自行宣布完整 S2 PASS。

