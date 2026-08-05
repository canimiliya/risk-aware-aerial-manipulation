# S4-R0-R2 真实机器人视觉管线解崩与稳定录制报告

## 结论

本轮未达到 READY。最终标签：
`BLOCKED_S4_R0_R2_NATIVE_VISUAL_PIPELINE_UNRESOLVED`。

控制、动力学、质量和反作用结果没有改变，仍保留此前通过的 11 组 headless 结果。本轮实现了 link 级真实 USD 绑定候选、独立 P0–P3 进程矩阵、路线 B flatten cache 审计和 base/head pytest 对照，但当前 Isaac native runtime 仍不能稳定产出可审计的 R2 live viewport 证据。因此没有伪造或提升旧证据，R2 PNG/video/curve 数量按 0 记录。

## 1. Git/PR 与边界

- branch：`agent/s4-r0-nominal-dynamics-control`
- start Head：`f268ea800a93c1e82e4bb303b3ee27fa51ab80ab`
- base main：`741dd82e823420e0d8b272c9f06ed81b0b757183`
- PR #14：Open、Draft、未合并
- 正式进度：`4/9≈44%`
- S4：`IN_PROGRESS`
- S4-R0：`SUBMITTED_FOR_REVIEW`
- S5–S8：`FROZEN`

没有启动其他代理，没有进入完整 AM-Planner 轨迹闭环、风、接触任务、训练或 S5。

## 2. P0–P3 独立矩阵

矩阵文件为 `docs/evidence/S4-R0/visuals/r2/visual_crash_matrix.json`。每个 probe 都由独立 Isaac 进程执行：

| Probe | 最后完成阶段 | 结果 |
|---|---|---|
| P0 静态真实 USD + capture | `PHASE_STATIC_CAPTURE` | native exit |
| P1 20 次默认时间 root 更新 + capture | `PHASE_ROOT_DEFAULT_UPDATE_COMPLETE` | native exit |
| P2 20 次真实 `AA_1` link 默认时间更新 + capture | `PHASE_LINK_DEFAULT_UPDATE_COMPLETE` | native exit |
| P3 20 次 live PhysX 更新 + capture | `PHASE_LIVE_LOOP_COMPLETE` | native exit |

最小可复核触发组合是：真实 USD 加载后进入 viewport capture；P1/P2/P3 说明默认时间 root/link 更新和 live PhysX 后的 capture 均不能形成稳定结果。禁止的 `Usd.TimeCode` 主动画路线、`stage.SetTimeCode` 和预写 timeline 均未使用。

## 3. 真实资产与 cache

源资产固定为 `D:/i3/a/aerial_manipulator_v2.usd`，SHA-256 为 `74cce4b4cd8a41da9b60829482debbf3a78c0548bacb9dd53089e92c5ed7bc7d`。候选 link 映射覆盖 `body`、`end_effector`、`AA_1/2/3` 和 `TA_1l/1r/2l/2r/3l/3r`，运行时来源为 post-PhysX root readback 加 official Delta kinematics。

路线 B flatten 输出保存在本地 `outputs/local_visuals/S4-R0-R2/cache/aerial_manipulator_v2_visual_only.usdc`，不提交 Git。其 manifest 显示 `Mesh count = 0`，同时仍有 Physics schemas，所以不满足 cache 硬门槛；不能把 custom STL visual layer 宣称为标准 Mesh cache。

## 4. 视觉证据与 readiness

R2 final manifest 明确为 `available=false、pass=false`，R2 PNG/video/curve 分别为 `0/0/0`。旧 R0 的 12 PNG、3 GIF 和 3 curves 已保留，并标记为 `legacy_S4-R0_preserved_not_promoted_to_R2`，没有被重新标注为 R2 live evidence。

readiness：`BLOCKED_S4_R0_R2_NATIVE_VISUAL_PIPELINE_UNRESOLVED`。

`full_closed_chain_dynamics=false`、`full_nominal_trajectory_closed_loop=false`、`s4_final_ready=false`、`s5_ready=false`。physics contact 语义仍是不可用；安全证据仍是 sampled-proxy clearance only。

## 5. base/head pytest

在同一 `D:/i3/e/python.exe` 环境运行 `pytest -q`：

- base `741dd82e...`：65 passed, 13 failed
- head `f268ea8...`：79 passed, 13 failed
- head-only failures：0
- 13 个失败是共同历史 S0/S1/S2 audit 输入、冻结 S3 点云或 manifest hash 问题；没有修改历史证据制造通过。

定向 R2/R1/S4 套件：`20 passed`。

## 6. 下一步边界

本轮在硬阻塞处停止。不能仅凭旧截图、state replay 或 cache manifest 关闭 R2，也不能关闭 S4、把 PR 标记 Ready、合并 PR 或推进 S5。后续需要稳定真实 S3 custom-STL live viewport 管线，或由负责人明确授权新的技术路线。
