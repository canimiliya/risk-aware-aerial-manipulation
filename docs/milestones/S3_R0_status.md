# S3-R0 status

- 正式阶段：`3/9≈33%`；工程估算：约 `41%`；S3 可审计完成度：约 `90%`
- S3：`IN_PROGRESS`；S3-R0：`SUBMITTED_S3_R0_PLAYBACK_READY_VALIDATION_INCOMPLETE`
- S4–S8：`FROZEN`

## R5 已完成

- 真实 Isaac API probe：`PASS`。`UsdPhysics.Scene` 没有 `CreateTimeStepsPerSecondAttr`；`PhysxSchema.PhysxSceneAPI` 有；`SimulationCfg(dt=1/240)` 实际 physics dt 为 `0.004166666666666667 s`，PhysicsScene、scene query 和零重力均正确。
- 删除错误的手工 `UsdPhysics.Scene.CreateTimeStepsPerSecondAttr()` 调用；由 `SimulationContext(SimulationCfg(...))` 统一创建和配置 `/World/PhysicsScene`。
- 1-step smoke：`PASS`；64-step smoke：`PASS`，`64/64`、heartbeat/checkpoint、state log、scene export 和 `APP_CLOSED` 均有证据。
- nominal headless ×3 与 repeat：均完成 `1255/1255`，最终时间 `5.223430863911155 s`，时间误差 `0`，FK 通过，精确 sampled-proxy clearance `0.06324289427326649 m`，contact/penetration/expanded overlap 通过。

## 尚未通过

- 固定距离门槛失败：`G1-G2=0.02947413222950797 m > 0.002 m`；`G2-G3=0.0006150516324444633 m` 通过。因此 `s3_kinematic_playback_accepted=false`。
- GUI、8 PNG、2 个本地视频和 visual manifest 未运行；因数值门槛已失败，按顺序停止。
- `full_closed_chain_dynamics=false`、`s4_dynamic_articulation_ready=false`，不进入 S4。

历史 R4 失败/中断证据保留，不能被 R5 结果覆盖。Isaac immediate shutdown 采用主线程 `app.close(skip_cleanup=True)`，因为本环境 graceful stage teardown 会阻塞；该行为已在 progress 中记录。
