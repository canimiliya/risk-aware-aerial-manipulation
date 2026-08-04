# S3-R0 status

- 正式阶段：`3/9≈33%`；整体工程估算：约 `44%`；S3 工程完成度：`100%`
- S3：`IN_PROGRESS`；S3-R0：`SUBMITTED_S3_R0_GEOMETRY_ENVELOPE_FAILED`（已提交审查，未宣布 S3 PASS）
- S4–S8：`FROZEN`

## R6 已完成

- 新增只读 `build_point_groups("nominal")`：`TargetProxy`、`MainBeam`、`Column`、`AdjacentObstacle` 四组 union 与 `build_points("nominal")` 完全一致，点数 `29984`，SHA-256=`79eab0b6a5f4aadcba6469ef3b0c1c50efb449ef58a53c1916edfc658c299145`，未改变 S2 点云。
- 旧 `|G1-G2|<=0.002 m` 合同已废止。G1 是 Isaac AABB sampled-proxy 距离，G2 是 S2 nominal 点云 sampled-proxy 距离，G3 是历史 S2-R6 2000 Hz 距离；`G1-G2` 仅作为 representation diagnostic，`geometry_representation_conservatism_m=G2-G1`。
- 现有四次 formal state logs 纯 Python 重算：G1=`0.06324289427326649 m`，G2=`0.09271702650277446 m`，G3=`0.09210197487032999 m`；`|G2-G3|=0.0006150516324444633 m`，Isaac 安全门槛和逐帧 `G1<=G2+1e-9 m` 均通过。

## R5 已完成

- 真实 Isaac API probe：`PASS`。`UsdPhysics.Scene` 没有 `CreateTimeStepsPerSecondAttr`；`PhysxSchema.PhysxSceneAPI` 有；`SimulationCfg(dt=1/240)` 实际 physics dt 为 `0.004166666666666667 s`，PhysicsScene、scene query 和零重力均正确。
- 删除错误的手工 `UsdPhysics.Scene.CreateTimeStepsPerSecondAttr()` 调用；由 `SimulationContext(SimulationCfg(...))` 统一创建和配置 `/World/PhysicsScene`。
- 1-step smoke：`PASS`；64-step smoke：`PASS`，`64/64`、heartbeat/checkpoint、state log、scene export 和 `APP_CLOSED` 均有证据。
- nominal headless ×3 与 repeat：均完成 `1255/1255`，最终时间 `5.223430863911155 s`，时间误差 `0`，FK 通过，精确 sampled-proxy clearance `0.06324289427326649 m`，contact/penetration/expanded overlap 通过。

## R6 阻塞项

- 保守包络证明失败：`Column` 组有 `1` 个 S2 nominal 点 `[0,0,0.08] m` 位于当前 S3 Column AABB 外，最大 outside distance=`0.009999999999999967 m`。该点由 `0.02 m` 体素取整导致；按合同不得扩大/移动 AABB 自动修复，必须先由负责人决定几何合同修正。
- 因几何包络门槛失败，GUI、8 PNG、2 个本地视频和 visual manifest 未运行；这不是视觉失败，而是按 R6 顺序停止。
- 因此 `s3_kinematic_playback_accepted=false`，但 playback/FK/clearance/state replay 独立检查均保留其真实结果。
- `full_closed_chain_dynamics=false`、`s4_dynamic_articulation_ready=false`，不进入 S4。

历史 R4 失败/中断证据保留，不能被 R5 结果覆盖。Isaac immediate shutdown 采用主线程 `app.close(skip_cleanup=True)`，因为本环境 graceful stage teardown 会阻塞；该行为已在 progress 中记录。
