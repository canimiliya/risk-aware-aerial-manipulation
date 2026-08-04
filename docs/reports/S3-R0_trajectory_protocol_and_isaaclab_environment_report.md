# S3-R0-R4 姿态、时间轴、Playback 活性诊断与最终验证报告

## 结论

本轮保留旧 pip-only/flatdict 失败现场，复用已通过的 Isaac Sim 5.1/Isaac Lab v2.3.2 环境。协议层已完成姿态、世界系和时间轴修正；R4 playback runner 已完成本地结构修正，但 64-step smoke 尚未执行，故本报告不宣称 S3 PASS。

协议现在保存 `base_quaternion_WB_wxyz`、`base_body_omega_B_rad_s`、`base_thrust_N`，姿态来源为 `S2_OFFICIAL_FLATNESS_MAP_RECONSTRUCTION`，并通过 `planner_bridge.execution.playback_validator.validate_attitude` 复用 S2 实现。world EE 使用 `p_WB + R_WB @ (R_BA0 @ p_A0E + t_BA0)`；工具方向使用 `R_WB @ R_BA0 @ direction_A0`，不虚构完整末端四元数。

240 Hz 时间网格使用 `simulation_time[k]=min(k*1/240,total_duration)`，并且直接从 raw base/arm polynomial 求值；本轮没有把 200 Hz bundle 帧逐帧当作 PhysX 步。R4 runner 的正式循环调用 Isaac Lab `SimulationContext.step(render=False)`，初始化阶段的 `app.update()` 仅用于有界 stage/reference warmup；`--smoke-steps`、`--max-runtime-s`、heartbeat、checkpoint、progress JSONL、partial state 和 atomic result 均已实现。由于 R4 smoke 尚未执行，expected/actual physics steps 与最大时间误差尚无新运行证据。

导入 USD 没有可初始化的完整 articulation root，因此使用任务卡允许的 `S3_KINEMATIC_PLAYBACK_ARTICULATION`：三 active joints 通过 PhysicsJointStateAPI 写入/读回，关闭未建模关节物理约束，passive/trailing joints 保持锁定语义。写入值与读回值一致；原始参考到 float32 USD 存储的最大量化差为 `1.4888097199516892e-08 rad`，该数值单独保留，未隐藏。

历史 nominal 1046 帧运行 exit 0、finite、时间单调和 overlap 下界证据继续保留，但它不是修正版合同的验收来源。修正版 nominal headless 命令已记录为中断，无结果文件；因此精确 sampled-proxy 指标必须保持未验证，不能从历史 overlap 下界推导。

## 环境

- 旧环境 `D:\i3\s3_isaaclab_232` 只读保留；失败现场在 `docs/evidence/S3-R0/environment/failed_pip_only/`。
- 正式环境 `D:\i3\e`；源码 `D:\i3\L`，tag `v2.3.2`，HEAD `37ddf626871758333d6ed89cf64ad702aef127d0`。
- `flatdict==4.0.1`：sdist SHA-256 `CD32F08FD31ED21EB09EBC76F06B6BD12046A24F77BEB1FD0281917E47F26742`；wheel SHA-256 `709AA498F998AB2AB7E63911935D0D135944EA34F3DB306837175AA7F8F828AA`。
- Isaac Sim `5.1.0.0`、Isaac Lab `0.54.2`、Torch `2.7.0+cu128`、CUDA=True、GPU RTX 5060 Ti。
- EULA 已真实接受；10-step empty-stage/PhysX smoke PASS。
- `pip check` 仍有已记录的 Isaac Lab/Isaac Sim `starlette` 上游元数据冲突；未改源码。

## 资产与场景

- 官方 AM-Planner Delta Xacro/mesh 只读审计完成，USD 外部保存于 `D:\i3\a\aerial_manipulator_v2.usd`，未提交。
- 9 个 revolute joints：3 active (`m1_1,m2_1,m3_1`) + 6 passive/trailing；完整闭链动力学未宣称。
- 场景 prim：`/World/Robot`、`/World/Crossarm/MainBeam`、`/World/Crossarm/Column`、`/World/Crossarm/AdjacentObstacle`、`/World/TargetProxy`。

## 播放与安全

- `REFERENCE_STATE_PLAYBACK`，`physics_dt=1/240`，`rendering_dt=1/60`，`num_envs=1`。
- nominal：1046 帧，`5.223430863911155 s`，exit 0，finite，时间单调。
- FK：通过。
- joint write/readback：写入 float32 值与读回一致；原始参考量化误差最大 `1.4888e-08 rad`。
- scene-query：无非场景命中；0.010 m 扩展盒无机器人命中；penetration=0。
- 精确指标名称应为 `EXACT_FOR_FROZEN_S2_SAMPLED_PROXY_NOT_MESH_EXACT`；当前尚无该指标的 Isaac read-back 运行结果。
- G1/G2/G3 distance delta、nominal×3、nominal repeat、GUI、8 PNG 和 2 个本地视频尚未完成。

## 测试与范围边界

- `PYTHONPATH=<repo> python -m pytest -q tests planner_bridge`：`64 passed in 80.24s`。
- S3 audit：协议检查通过；播放、时间轴、精确距离、S2 delta、repeat、GUI、visual manifest 均明确报告为缺失，不以历史旧 bundle 代替。
- S2 baseline：PASS。
- 未修改 S2 轨迹/barrier/anchor/tau/100w0；未改 Isaac Lab 上游依赖；未安装 RL framework；未建 ROS/ROS2 bridge；未训练、未闭环、未加风或接触随机化；未进入 S4；未合并 PR。`full_closed_chain_dynamics=false`、`s4_dynamic_articulation_ready=false`。

## R4 当前未完成项

- 尚未运行 64-step physics-only smoke；因此没有可宣称的 startup/step wall-time、heartbeat、checkpoint、graceful close 或活性结论。
- 尚未运行 nominal×3、nominal repeat、GUI、read-back FK、精确 sampled-proxy clearance、G1/G2/G3、8 PNG 和 2 个本地视频。
