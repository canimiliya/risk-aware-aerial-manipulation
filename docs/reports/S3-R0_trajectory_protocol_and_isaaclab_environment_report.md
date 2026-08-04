# S3-R0-R8 Column 几何合同、单一事实源与真实时序视觉收口报告

## 结论

R7 数值合同和静态场景证据保持不变；R8 已补齐授权范围内的危险时刻真实 GUI 截图与按时间推进的视频。当前提交标签为 `SUBMITTED_S3_R0_BASIC_ENVIRONMENT_READY`，readiness 为 `READY_FOR_S3_FINAL_REVIEW`；这不等于 S3 正式 PASS 或关闭。

正式状态：`3/9≈33%`，整体工程估算约 `44%`，`S3=IN_PROGRESS`，`S4–S8=FROZEN`。PR #13 保持 Open + Draft + 未合并。

## Column 修正与单一事实源

- 旧 Column：center=`[0,0,0.735]`，size=`[0.12,0.12,1.29]`，bounds=`x/y[-0.06,0.06], z[0.09,1.38] m`。
- 新 Column：center=`[0,0,0.73]`，size=`[0.12,0.12,1.30]`，bounds=`x/y[-0.06,0.06], z[0.08,1.38] m`。
- 只改变 z 轴；上边界保持 `1.38 m`，下边界精确覆盖冻结 S2 点云最小 `z=0.08 m`，无经验 padding。
- `planner_bridge/scenes/s3_r0_scene_contract.py` 导出不可变 world-frame `SCENE_AABBS`；playback、distance audit、correspondence evidence 和测试均读取同一合同。其他三个障碍未修改。
- USD 写入使用 double-precision Xform scale，避免 `Vec3f` 量化超过 `1e-9 m` read-back 门槛。

## Scene contract 与 world EE

`docs/evidence/S3-R0/scene_contract.json` 以及两个轨迹 bundle 使用完整合同：`p_WB_plus_R_WB_(R_BA0_p_A0E_plus_t_BA0)`；audit 现在检查 docs/bundle 共有字段、B→A0 变换、WXYZ、tool direction 和旧表述不存在。实际 world EE 计算方法未改变。

## 点云与距离合同

- 四组：TargetProxy=`24948`、MainBeam=`2601`、Column=`1802`、AdjacentObstacle=`1269`。
- union count=`29984`，与 `build_points("nominal")` 完全一致；冻结 SHA-256=`79eab0b6a5f4aadcba6469ef3b0c1c50efb449ef58a53c1916edfc658c299145`。
- 四组 containment：outside_count 全部为 `0`，max outside distance 全部为 `0.0 m`，全局通过。
- 四次既有 state logs 未重跑，仅以纯 Python 重算：G1=`0.06324289427326649 m`，G2=`0.09271702650277446 m`，G3=`0.09210197487032999 m`；`|G2-G3|=0.0006150516324444633 m`。
- G1 危险项=`rotor_4/AdjacentObstacle`，`1.3708333333333333 s`；G2 危险项=`rotor_4`，最近点=`[-0.04,0.62,1.68] m`。
- 所有 run/frame/component 满足 `G1<=G2+1e-9 m`；`geometry_representation_conservatism_m=G2-G1=0.02947413222950797 m` 仅作诊断。旧 `|G1-G2|<=0.002 m` 门槛仍废止。

## Isaac read-back 与运行

`isaac_scene_aabb_readback.json` 对 corrected smoke 导出的 USD 逐 prim 读回四个 AABB：全部 PASS，逐轴误差 `<=1e-9 m`；Column 实际 z bounds=`[0.07999999999999996,1.38] m`。

- corrected 64-step smoke：`64/64`，scene USD 导出成功，应用关闭正常。
- corrected nominal GUI：`1255/1255`，完整 duration、时间对齐、finite、contact、G1、arm FK 和 world EE 均通过；最大 arm/world residual 分别为 `1.642394602096004e-09/1.6423945397297966e-09 m`。
- corrected nominal_repeat GUI：同样 `1255/1255`，上述门槛全部通过。
- 两次 GUI 均使用 `--disable-joint-physics`，避免参考状态被关节物理扰动。首次未带该选项的 GUI 结果保留为真实失败诊断，未冒充通过。

## 视觉证据

`docs/evidence/S3-R0/visuals/manifest.json` 记录 8 张真实 Isaac GUI viewport PNG：nominal/repeat 各整体、侧视、俯视、近景 4 张，均含来源、frame/time、bytes 和 SHA-256。两个本地 GIF 位于 `outputs/local_visuals/S3-R0-R7/`，manifest 记录 path、SHA、bytes、duration=`1.6 s`、fps=`2.5`、尺寸=`1280x720`，`committed=false`；视频未提交 Git。

## R8 真实时序视觉证据

- `nominal_gui_r8_real_timeline` 与 `nominal_repeat_gui_r8_real_timeline` 各执行一次 GUI state-replay，均 `1255/1255`、scene output 成功、应用正常关闭；R8 未重跑既有 nominal headless×3 或 repeat headless×1。
- 每个 run 新增 15 张真实 Isaac viewport PNG：overall 序列 frame=`0,100,200,280,327,329,331,400,600,800,1000,1150,1254`，并在危险 frame `329` 和最终 frame `1254` 增加 close 图。对应危险 time=`1.3708333333333333 s`，满足 frame ±2 与 time ±2/240 s；加上保留的 R7 8 张 PNG，manifest 总数=`38`。
- 两个本地 GIF 位于 `outputs/local_visuals/S3-R0-R8/`，各 `13` 帧、`1280x720`、`1.3 s`、`10 fps`，固定 overall 相机；manifest 保存完整 source frame/time、PNG SHA、state SHA、SHA-256、bytes、duration、尺寸、chronological/start/danger/final flags，`committed=false`。两者均被 audit 重新解码并确认至少两帧视觉不同。
- `scripts/s3_r0_gui_visual_capture.py` 只合并并验证真实 state-replay 采集，保留 R7 legacy evidence；`scripts/s3_r0_visual_video_manifest.py` 拒绝重复 frame/time、缺失危险/起止覆盖或静态帧序列；新增回归测试证明同一时间多视角幻灯片会被拒绝。

## 测试与边界

本轮最新全量复核为 `python -m pytest -q tests planner_bridge`：`71 passed, 6 failed`；新增 R8 视觉合同测试通过，6 个失败均为开始 Head 已存在的 S0/S1/S2 历史审计节点，未新增失败。

补充合同接口后的最新复核：视觉合同测试 `2 passed`，R7/R8 相关定向测试合计 `23 passed`；全量结果更新为 `72 passed, 6 failed`，失败 node 未变化，仍未新增失败。

R8 targeted tests：`tests/test_s3_r0_visual_contract.py`、`tests/test_s3_r0_distance_representation.py`、`tests/test_s3_r0_protocol.py`=`20 passed`；`tests/audit/test_s3_s2_baseline.py`=`4 passed`；四个 R8 脚本 py_compile 通过；readiness audit `errors=[]`、`warnings=[]`。全量 `python -m pytest -q tests planner_bridge` 仍为 `70 passed, 6 failed`；6 个失败 node id 与开始 Head 相同：`tests/audit/test_audit_no_side_effects.py::test_historical_audits_leave_status_and_acceptance_bytes_unchanged`、`tests/audit/test_check_s0_structure.py::test_current_s0_audit_passes`、`tests/audit/test_s1_audit_no_side_effects.py::test_default_run_does_not_rewrite_historical_acceptance`、`tests/audit/test_s1_audit_no_side_effects.py::test_external_output_is_supported`、`tests/audit/test_s2_r0_archival_audit.py::test_archival_passes_without_local_npz`、`tests/audit/test_s2_r0_archival_audit.py::test_final_acceptance_passes_archival_mode_and_forwards_it`。根因仍是 S0 no-large-files 发现未跟踪的 formal S3 JSON 与下游 archival 依赖该结果；本轮未删除证据、未修改历史 acceptance。

历史 S1/S2 acceptance SHA 与开始 Head 对照全部 unchanged：`s1_final_acceptance bf4225a1...`、S2-R0 preflight `eee5dfa2...`、S2-R0 final `b4673b62...`、S2-R1 `f86ffd96...`、S2-R4 `fb5c2869...`、S2-R5 `0e95a47d...`、S2-R6 `3cea841a...`。

未修改 S2 点云、轨迹、barrier、anchor、tau、100w0、Isaac Lab/Sim 上游或环境；未训练、未闭环、未接 ROS/ROS2、未进入 S4、未关闭 S3、未将 PR 标记 Ready、未合并 PR。

最终证据目录：`docs/evidence/S3-R0/distance_representation/`；最终 readiness：`docs/evidence/S3/final_readiness/s3_final_readiness.json`。
