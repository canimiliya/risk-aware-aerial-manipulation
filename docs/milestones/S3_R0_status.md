# S3-R0 status

- 正式阶段：`3/9≈33%`；整体工程估算：约 `44%`；S3 工程完成度：`100%`（工程证据已提交复核，不代表高级总控已验收）。
- S3：`IN_PROGRESS`；S3-R0：`SUBMITTED_S3_R0_BASIC_ENVIRONMENT_READY`；readiness：`READY_FOR_S3_FINAL_REVIEW`。
- S4–S8：`FROZEN`。

## R7 已完成

- Column 从 center `[0,0,0.735]` / size `[0.12,0.12,1.29]` 最小修正为 `[0,0,0.73]` / `[0.12,0.12,1.30]`，world bounds 下边界精确到 `z=0.08 m`，上边界保持 `z=1.38 m`。
- 新增不可变 `planner_bridge/scenes/s3_r0_scene_contract.py`，playback、distance audit、correspondence 与测试共用 `SCENE_AABBS`；其余障碍和全部 S2 冻结产物未修改。
- 修正独立 scene contract 的完整 B→A0 world EE 公式，并在 audit/test 中检查 bundle/docs 一致性及旧表述不存在。
- 四次既有 formal state logs 纯 Python 重算：G1=`0.06324289427326649 m`、G2=`0.09271702650277446 m`、G3=`0.09210197487032999 m`、`|G2-G3|=0.0006150516324444633 m`；containment 四组 outside=0；逐帧 `G1<=G2+1e-9 m` 通过。
- corrected Isaac 64-step smoke、nominal GUI、nominal_repeat GUI 均已完成；GUI 均 `1255/1255`，FK/world EE/contact/time alignment/clearance 通过。
- 完成 Isaac USD AABB read-back：四个 prim 每轴误差 `<=1e-9 m`；完成 8 张真实 GUI PNG、2 个本地 GIF 和 manifest。

## R8 视觉证据补齐

- 保留 R7 的 8 张最终状态 PNG 与 2 个旧 GIF，并在 `docs/evidence/S3-R0/visuals/r8/` 新增 nominal/repeat 各 15 张真实 Isaac GUI state-replay PNG；总 manifest PNG=`38`。
- 新增截图由 `s3_r0_reference_playback.py` 在对应 `sim.step(render=True)` 后采集，记录真实 `source_frame/source_time_s`、PNG SHA、bytes 和 state SHA；nominal/repeat 均覆盖 frame `329±2`、time `1.3708333333333333±2/240 s` 及最终 frame `1254`。
- 重新生成两个本地时序 GIF：每个 `13` 帧，严格覆盖 frame `0,100,200,280,327,329,331,400,600,800,1000,1150,1254`，同一 overall 相机，manifest 记录 source frame/time、state/image SHA、运动差异、物理 GIF 元数据；视频 `committed=false`。
- audit 已增强为独立验证 PNG 文件 SHA/bytes、危险/起始/最终覆盖、视频真实帧数/时长/尺寸、严格时序、危险时刻、source image/state 差异和非静态运动；同一时间的视角幻灯片回归测试已加入。

## 约束与状态

- 旧 `|G1-G2|<=0.002 m` 只保留为废止说明；`geometry_representation_conservatism_m=G2-G1` 作为诊断。
- formal nominal headless×3 与 nominal_repeat headless×1 使用既有日志，R7 未重复运行。
- 失败诊断证据保留；R7/R8 视频只在本地保存，不提交 Git，R8 PNG 提交 Git。
- 不进入 S4，不做闭环/ROS/训练/动力学扩展，不关闭 S3；等待高级总控独立 S3 final review。
