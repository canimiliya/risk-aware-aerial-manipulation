# S3-R0-R2 官方源安装与 Isaac Lab 仿真闭环报告

## 结论

本轮已解决旧 pip-only 安装路线的 `flatdict==4.0.1` 构建阻断：新环境按官方 Isaac Sim 5.1 pip package → Isaac Lab v2.3.2 官方源码 → `isaaclab.bat -i none` 安装并运行。Isaac Sim empty-stage/PhysX 冒烟、官方 AM-Planner Delta 资产导入、横担场景构建和名义轨迹 1046 帧播放均完成。

但播放后的关节回读误差为 `0.01098238426654774 rad`，项目 arm FK 最大误差为 `0.18227038753484998 m`，world EE 最大误差为 `0.18227038753484992 m`，均超过硬门槛；接触查询未实现，clearance 未执行。因此最终标签为 `SUBMITTED_S3_R0_FK_FAILED`，不宣称 S3 PASS，不进入 S4。

## 进度口径

- 正式阶段：`3/9 ~= 33%`，本轮不跨阶段。
- 工程估算：约 `42%`。
- S3-R0：约 `80%`：环境、资产、场景和运行时播放已完成，但 FK/安全门槛未通过。

## 环境

- 旧环境 `D:\i3\s3_isaaclab_232` 只读保留，旧失败现场在 `docs/evidence/S3-R0/environment/failed_pip_only/`。
- 正式环境 `D:\i3\e`；源码 `D:\i3\L`，tag `v2.3.2`，HEAD `37ddf626871758333d6ed89cf64ad702aef127d0`。
- `flatdict==4.0.1`：官方 PyPI sdist SHA-256 `CD32F08FD31ED21EB09EBC76F06B6BD12046A24F77BEB1FD0281917E47F26742`；本地纯 Python wheel SHA-256 `709AA498F998AB2AB7E63911935D0D135944EA34F3DB306837175AA7F8F828AA`。
- `isaacsim==5.1.0.0`、`isaaclab==0.54.2`、Torch `2.7.0+cu128`、CUDA 可用、GPU 为 RTX 5060 Ti。
- EULA 已通过真实 `echo Yes | isaacsim.exe --help` 接受；10-step empty-stage/PhysX smoke 为 PASS。
- `pip check` 留有一个已知上游元数据冲突：Isaac Lab 要求 `starlette==0.49.1`，而 Isaac Sim 的 `fastapi==0.115.7` 要求 `starlette<0.46`。保留 Isaac Sim 严格运行时 pins：`fastapi==0.115.7`、`starlette==0.45.3`，未修改 Isaac Lab 源码。
- `isaaclab_rl` 是官方基础包；未安装 `rsl_rl`、`rl_games`、`skrl`、SB3 或 `robomimic`。

## 资产、场景与播放

- 官方 AM-Planner Delta Xacro/mesh 只读审计完成，导入外部 USD `D:\i3\a\aerial_manipulator_v2.usd`，未提交大资产。
- 导入观察到 9 个 revolute joint：3 active (`m1_1,m2_1,m3_1`) + 6 passive/trailing；root `/delta_display/body`，51 个 prim，mesh resolve errors 为 0。保留 body mass 和 STL attribute warning。
- 场景 prim：`/World/Robot`、`/World/Crossarm/MainBeam`、`/World/Crossarm/Column`、`/World/Crossarm/AdjacentObstacle`、`/World/TargetProxy`。几何复用既有 scene contract，没有修改 S2 几何。
- `REFERENCE_STATE_PLAYBACK`、`physics_dt=1/240`、`rendering_dt=1/60`、`num_envs=1`；nominal 1046 frames、运行时长 `5.223430863911155 s`、观测 step 1046、有限且时间单调，脚本 exit 0。
- repeat、GUI、视频/PNG 可视化、接触和 clearance 没有执行，不能以缺失数据代替 PASS。

## FK 与安全

| 指标 | 实测 | 门槛 | 结果 |
|---|---:|---:|---|
| joint state readback | 0.01098238426654774 rad | <=1e-8 rad | FAIL |
| arm FK residual | 0.18227038753484998 m | <=1e-5 m | FAIL |
| world EE residual | 0.18227038753484992 m | <=1e-4 m | FAIL |
| contact query | 未实现 | non-target contacts=0 | NOT EXECUTED |
| clearance | 未执行 | >=0.010 m | NOT EXECUTED |

当前应先定位 USD joint state 写入/回读、frame mapping 与项目 Delta FK 的差异，再执行真实 PhysX contact/distance 证据；不得通过放宽门槛或缩小 proxy 修复。

## 测试与证据

- `pytest -q tests planner_bridge`：`62 passed`。
- S2 baseline：`PASS`。
- Isaac Sim custom smoke：10 steps、PhysX scene、finite、exit 0。
- S3 playback：runtime loop 完成，但 FK gate failed。
- 外部安装目录、cache、USD 和生成 URDF 未提交；PR #13 保持 Draft。

## 范围边界

未修改 S2 轨迹、barrier、anchor、tau 或 `100w0`；未改 Isaac Lab 上游依赖；未安装 RL framework；未建 ROS/ROS2 bridge；未训练、未做闭环控制、未加风或接触随机化；未进入 S4；未合并 PR。
