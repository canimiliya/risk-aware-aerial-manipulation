# S3-R0-R6 距离表示合同、保守性证明与最终收口报告

## 结论

本轮完成 R6 距离表示合同纠正、四次既有 state log 纯 Python 重算和保守性审计。旧 `|G1-G2|<=0.002 m` 门槛无效，因为 G1 是 Isaac 实体 AABB envelope，G2 是 S2 的 `0.02 m` 体素/圆柱代理点云；两者不是同一种障碍几何。当前仍不能收口通过，阻塞点是保守包络证明：Column 组有一个 S2 点落在当前 S3 Column AABB 外。

正式状态：`S3=IN_PROGRESS`，`S3-R0=SUBMITTED_S3_R0_GEOMETRY_ENVELOPE_FAILED`，`S4–S8=FROZEN`。

## R6 距离合同与证明

- `build_point_groups("nominal")` 四组为 `TargetProxy`、`MainBeam`、`Column`、`AdjacentObstacle`；union 点数=`29984`，与原 `build_points("nominal")` 完全一致，SHA=`79eab0b6a5f4aadcba6469ef3b0c1c50efb449ef58a53c1916edfc658c299145`。
- G1=`0.06324289427326649 m`，危险组件=`rotor_4`，障碍=`AdjacentObstacle`，时间=`1.3708333333333333 s`；满足 G1≥`0.010 m`。
- G2=`0.09271702650277446 m`，危险组件=`rotor_4`，最近点=`[-0.04,0.62,1.68]`，时间=`1.3666666666666667 s`。
- G3=`0.09210197487032999 m`，历史危险组件=`rotor_4`；`|G2-G3|=0.0006150516324444633 m`，通过。
- 全部四次 formal state logs 的逐帧 `G1<=G2+1e-9 m` 通过；`geometry_representation_conservatism_m=G2-G1=0.02947413222950797 m` 仅作表示差异诊断，不再作为 2 mm 硬门槛。
- 包含证明：TargetProxy、MainBeam、AdjacentObstacle 通过；Column `outside_count=1`，违规点=`[0,0,0.08] m`，最大 outside distance=`0.009999999999999967 m`，所以 `conservative_geometry_envelope=false`。

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
- G1-G2：不再是硬门槛；其正向保守量 `G2-G1=0.02947413222950797 m` 表示 AABB 距离更小、更保守。

## 范围与未执行项

GUI nominal、8 PNG、2 个本地 MP4/GIF、visual manifest 未执行，因为保守包络证明失败；未通过扩大/移动 AABB 自动修复。未修改 S2 点云、Isaac Lab/Sim 上游、USD、环境；未训练、未闭环、未接 ROS/ROS2、未进入 S4；PR #13 保持 Draft、未合并。

## 测试与审计

- R6 相关回归：`22 passed`（point-group contract、S2 map、S3 protocol、workspace、planner bridge）。全量 `python -m pytest -q tests planner_bridge`：`63 passed, 6 failed`；6 个失败仍是既有 S0/S1/S2 archival/large-file 状态基线问题，不涉及 R6 代码，未以修改历史证据的方式绕过。
- S3 audit：`SUBMITTED_S3_R0_GEOMETRY_ENVELOPE_FAILED`；`playback_runs=true`、`state_replay_s2_clearance_delta=true`、`framewise_conservative_order=true`，但 `s2_points_contained_by_isaac_aabbs=false`；GUI/视觉按顺序未执行。

距离证据目录：`docs/evidence/S3-R0/distance_representation/`，包含 correspondence、point-in-AABB、framewise G1/G2、per-component minima、formal summary 和文字报告。
