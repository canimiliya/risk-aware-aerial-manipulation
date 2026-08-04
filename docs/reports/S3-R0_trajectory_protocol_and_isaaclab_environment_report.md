# S3-R0-R2 官方源安装与 Isaac Lab 仿真闭环报告

## 结论

本轮保留旧 pip-only/flatdict 失败现场，改用官方 Isaac Sim 5.1 pip package → Isaac Lab v2.3.2 官方源码 → `isaaclab.bat -i none`。新环境可导入并完成 Isaac Sim empty-stage/PhysX smoke；官方 AM-Planner Delta 资产、横担场景和 nominal reference playback 均完成。

上一版播放脚本把协议 joint-state convention 错传给 `official_fk`，已修正为 `official_fk_joint_state`。修正后 arm FK 最大残差 `1.3877787807814457e-16 m`，world EE 最大残差 `2.220446049250313e-16 m`。

导入 USD 没有可初始化的完整 articulation root，因此使用任务卡允许的 `S3_KINEMATIC_PLAYBACK_ARTICULATION`：三 active joints 通过 PhysicsJointStateAPI 写入/读回，关闭未建模关节物理约束，passive/trailing joints 保持锁定语义。写入值与读回值一致；原始参考到 float32 USD 存储的最大量化差为 `1.4888097199516892e-08 rad`，该数值单独保留，未隐藏。

nominal 1046 帧运行 exit 0、finite、时间单调。PhysX scene-query 逐帧检查四个场景 proxy：排除场景自身预期重叠后，非场景命中为 0，0.010 m 扩展盒命中为 0，penetration 记录为 0。这是 `>=0.010 m` 的 overlap 下界证据，不是精确最小距离；精确 clearance 和 S2 delta 尚未完成。最终标签为 `SUBMITTED_S3_R0_PLAYBACK_FAILED`，不宣称 S3 PASS，不进入 S4。

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
- 精确 `min clearance`、S2 delta、nominal repeat、GUI 和可视化产物尚未完成。

## 测试与范围边界

- `pytest -q tests planner_bridge`：`62 passed`。
- S2 baseline：PASS。
- 未修改 S2 轨迹/barrier/anchor/tau/100w0；未改 Isaac Lab 上游依赖；未安装 RL framework；未建 ROS/ROS2 bridge；未训练、未闭环、未加风或接触随机化；未进入 S4；未合并 PR。
