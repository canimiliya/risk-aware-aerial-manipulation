# S3-R0 status

- S3-R0：`SUBMITTED_S3_R0_PLAYBACK_READY_VALIDATION_INCOMPLETE`
- 轨迹协议：`PASS`（动态 OfficialFlatnessMap 姿态、WXYZ、B→A0 和 raw-polynomial 240 Hz 时间网格）
- R4 playback runner：`IMPLEMENTED_NOT_YET_EXECUTED`（SimulationContext physics-only、64-step smoke、heartbeat/checkpoint、phase timeout、atomic result）
- Isaac Sim/Isaac Lab 基础运行：`READY_WITH_LIMITATIONS`
- 修正版 nominal/repeat/GUI 播放：`NOT_VERIFIED`
- 精确 sampled-proxy clearance 与 S2 delta：`NOT_VERIFIED`
- 可视化 manifest：`NOT_COMPLETE`
- S4–S8：`FROZEN`
- S4--S8：`FROZEN`

本轮已修正协议的三个合同问题：不再使用 identity quaternion/zero omega，改为复用 S2 `OfficialFlatnessMap` 重建并明确 `base_quaternion_WB_wxyz`；world EE 改为 `p_WB + R_WB @ (R_BA0 @ p_A0E + t_BA0)`；240 Hz 播放接口改为按 raw polynomial 在 `min(k/240,total_duration)` 求值。协议独立测试通过，nominal/repeat bundle 均通过动态姿态、四元数、旋转正交性和 B→A0 合同检查。

历史 nominal 播放证据仍保留，但它对应旧 identity/200 Hz 合同，不能替代本轮修正版播放。上一版修正版 runner 在有限等待内未产生结果文件，已停止并保存 `isaac_playback_nominal_corrected_interrupted.json`。本轮已将 runner 改为正式 `SimulationContext.step(render=False)` physics-only loop，并加入 `--smoke-steps`、heartbeat、checkpoint、阶段超时、partial state 和原子结果写入；R4 smoke 尚未执行，因此 240 Hz 实际步数、read-back FK、精确 sampled-proxy clearance、G1/G2/G3 delta、nominal×3、repeat、GUI 和 8 PNG/2 video 仍未验收。S3 不通过，不进入 S4。
