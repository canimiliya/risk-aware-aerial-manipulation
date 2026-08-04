# S3-R0-R5 姿态、时间轴、PhysicsScene API 与 Playback 验证报告

## 结论

本轮完成 R5 PhysicsScene API 兼容修复并取得真实 Isaac 运行证据，但 S3-R0 仍不能验收通过。阻塞点是固定的 G1/G2 精确距离一致性门槛，不是 PhysicsScene API、物理步活性、时间轴、FK 或 clearance 下界。

正式状态：`S3=IN_PROGRESS`，`S3-R0=SUBMITTED_S3_R0_PLAYBACK_READY_VALIDATION_INCOMPLETE`，`S4–S8=FROZEN`。

## API 与环境

- 环境：`D:\i3\e`；Isaac Lab 源码：`D:\i3\L`；Robot USD：`D:\i3\a\aerial_manipulator_v2.usd`。
- API probe：`PASS`。
  - `UsdPhysics.Scene.CreateTimeStepsPerSecondAttr=False`
  - `PhysxSchema.PhysxSceneAPI.CreateTimeStepsPerSecondAttr=True`
  - `physics_dt=0.004166666666666667 s`
  - `/World/PhysicsScene` 存在，scene query 开启，gravity=`(0,0,0)`。
- 播放脚本已删除错误的 `UsdPhysics.Scene.CreateTimeStepsPerSecondAttr()`；`SimulationCfg.dt` 是唯一 physics 时间配置源。USD stage time metadata 不作为 physics dt 验收依据。
- cleanup 改为主线程；当前 Isaac Sim graceful stage teardown 会阻塞，因此使用已记录的 `app.close(skip_cleanup=True)` immediate framework release。未使用 daemon thread。

## Playback

- 1-step smoke：`actual=1`，SimulationContext ready/reset、timeline playing、STEP_0、state/result、APP_CLOSED 均通过。
- 64-step smoke：`expected=64, actual=64`；heartbeat 每 8 步、checkpoint 每 16 步；总 wall time 约 `10.656 s`。
- nominal headless ×3 与 nominal repeat：均 `expected=1255, actual=1255`；每次最终时间 `5.223430863911155 s`，`max_time_alignment_error=0`，时间严格单调、finite、完整 duration 通过。
- 记录的完整运行预测 wall time 约 `0.39–0.41 s`，实际包含启动、后处理和关闭约 `25.6–25.9 s`；step median 接近 `0`，p95 约 `0.016 s`。

## FK 与距离

- 最大 arm FK residual：`1.642394602096e-09 m`，门槛 `1e-5 m`，通过。
- 最大 world EE residual：`1.6423945397298e-09 m`，门槛 `1e-4 m`，通过。
- 指标：`EXACT_FOR_FROZEN_S2_SAMPLED_PROXY_NOT_MESH_EXACT`。
- 最小 G1 analytic sampled-proxy clearance：`0.06324289427326649 m`，门槛 `0.010 m`，通过；dangerous component=`rotor_4`，obstacle=`AdjacentObstacle`。
- G2-G3：`0.0006150516324444633 m <= 0.002 m`，通过。
- G1-G2：`0.02947413222950797 m > 0.002 m`，失败；因此 distance match 与 S3 kinematic playback acceptance 失败。

## 范围与未执行项

GUI nominal、8 PNG、2 个本地 MP4/GIF、visual manifest 未执行，因为数值 distance gate 已失败。未修改 S2、Isaac Lab/Sim 上游、USD、环境；未训练、未闭环、未接 ROS/ROS2、未进入 S4；PR #13 保持 Draft、未合并。

## 测试与审计

- `python -m pytest -q tests planner_bridge`：`64 passed`。
- S3 audit：`SUBMITTED_S3_R0_PLAYBACK_READY_VALIDATION_INCOMPLETE`；errors=`s2_clearance_delta, gui, visual_manifest`；protocol、Isaac readiness、playback、FK、exact clearance 均有证据。
