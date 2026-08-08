# S4-R3 Native Multibody Skeleton R1

## 结论

本轮没有建立 native multibody skeleton，最终诚实结论为：

`BLOCKED_S4_R3_DELTA_TOPOLOGY_UNRESOLVED`

阻塞发生在真实 USD 资产/拓扑阶段：源 USD 暴露的是一棵树，不是 Delta 闭链；它没有浮动 UAV base，也没有把三条分支的远端 link 重新连接到共同末端的 passive/closure joints。因此本轮没有创建替代杆件、没有修改 R2 viewport、没有运行 surrogate 调参、没有启动 native 1000-step 或内部激励实验。

## 任务边界

- 起始 Head：`9aacfdafe8fdee00b3da45234f9acb81079abb78`
- 分支：`agent/s4-r3-native-multibody-skeleton`
- PR #14 保持 Open、Draft、未合并；没有修改、关闭或合并 PR #14。
- R2 保持冻结为 `BLOCKED_S4_R0_R2_NATIVE_VISUAL_PIPELINE_UNRESOLVED`。
- 没有生成 PNG、GIF、视频或 viewport 证据；没有进入 rotor、wind、contact、完整轨迹、RL 或 S5。

## 资产审计结果

针对 `D:/i3/a/aerial_manipulator_v2.usd` 及其 6 个 composed layers 进行了只读枚举。结果：

| 项目 | 结果 |
|---|---:|
| UAV base rigid body in source asset | `false` |
| 正质量 arm links | `10` |
| active joint candidates | `3`：`m1_1`, `m2_1`, `m3_1` |
| passive joint candidates | `6`：`m1_2`, `m1_3`, `m2_2`, `m2_3`, `m3_2`, `m3_3` |
| existing loop joints | `0` |
| articulation root found | `true`，但位于 Delta arm body，不是 floating UAV base |
| Delta loop reconstructable | `false` |

10 条源 joint 的 body relationship 均可读，但拓扑全部是 `end_effector -> branch link` 的星形树；没有 distal branch-to-end-effector closure edge。缺失项被记录为：`missing passive joint`、`link relationship`、`floating UAV base rigid body`。

## Runtime 与 readiness

由于资产 blocker，以下项目均按任务卡记为 `NOT_RUN_ASSET_BLOCKER`，不是零误差或 PASS：

- floating articulation：未建立；
- PhysX active/passive joint integration：未建立；
- loop residual：未测量；
- native 1000-step stability：未运行；
- internal torque-pulse reaction：未运行；
- momentum drift：未测量；
- native solver-generated base response：未验证。

旧 `Python arm integrator + manual reaction` 只作为 `LEGACY_SURROGATE` 保留；本轮没有把它包装成 native 结果。UAV 质量/惯量仍是 provisional，`hardware_parameter_validated=false`。

## 测试

- 新增 R3 fail-safe contract tests 与既有 S4/S3 定向测试：`27 passed, 0 failed`。
- 基线 `9aacfd...`：`84 passed, 13 failed`。
- 当前 Head：`93 passed, 13 failed`。
- `HEAD_ONLY_FAILURES=0`；新增 9 个通过项是本轮阻塞保护测试，13 个失败为原有历史 S0/S1/S2/S3 审计/冻结证据失败。

## 证据

- 资产总清单：`docs/evidence/S4-R3/asset/native_asset_manifest.json`
- 刚体清单：`docs/evidence/S4-R3/asset/rigid_body_manifest.json`
- 质量/惯量清单：`docs/evidence/S4-R3/asset/mass_inertia_manifest.json`
- Joint 清单：`docs/evidence/S4-R3/asset/joint_manifest.json`
- Layer 依赖：`docs/evidence/S4-R3/asset/layer_dependency_manifest.json`
- 拓扑判定：`docs/evidence/S4-R3/asset/delta_topology_manifest.json`
- Runtime manifest：`docs/evidence/S4-R3/runtime/native_runtime_manifest.json`
- Loop metrics：`docs/evidence/S4-R3/runtime/loop_closure_metrics.json`
- Internal reaction：`docs/evidence/S4-R3/runtime/internal_reaction_metrics.json`
- Momentum diagnostics：`docs/evidence/S4-R3/runtime/momentum_diagnostics.json`
- State-write audit：`docs/evidence/S4-R3/runtime/state_write_audit.json`
- Readiness：`docs/evidence/S4-R3/summary/s4_r3_readiness.json`
- Base/head pytest：`docs/evidence/S4-R3/tests/base_vs_head_pytest.json`

## 最终 10 项回答

1. 当前 Head：本报告提交后以最终 Git handoff SHA 为准；起始 Head 为 `9aacfdafe8fdee00b3da45234f9acb81079abb78`。
2. floating articulation：否。
3. dynamic links：源资产有 `10` 个正质量 arm links；没有 native runtime dynamic-link 实例。
4. 三个主动关节由 PhysX solver 积分：否，未建立 native skeleton。
5. 被动关节由 PhysX solver 积分：否，未建立 native skeleton。
6. Delta loop closure：否；源资产现有 loop joint 数为 `0`。
7. 最大 loop residual：未测量，记为 `null`。
8. native 是否停止人工 reaction/gravity：否；native mode 未实现，旧路径仅保留为 legacy surrogate。
9. arm 运动时 base 是否自然响应：未验证，记为否/未运行。
10. R3：`BLOCKED_S4_R3_DELTA_TOPOLOGY_UNRESOLVED`。

已经真正解决了：真实 USD 的 link、joint、MassAPI、关节限制、drive 属性、body relationship 和 layer 依赖已机器可读审计；并证明现有资产不是可直接 closure 的 Delta multibody。
还缺：浮动 UAV base、缺失的 distal passive/closure joints、PhysX articulation tree、closure constraint、solver readback 和无 surrogate runtime。
下一任务：先由项目负责人决定是否修复/替换权威 USD 物理资产；在资产拓扑可唯一恢复前，不进入 R4 rotor。
