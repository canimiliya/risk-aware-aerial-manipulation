# S2-R5 adaptive task-level arm-envelope constraints report

## 项目进度

- 正式阶段：22%（2/9），本轮未推进正式阶段。
- 工程估算：本轮证据包完成，约 100%；S2 仍为 `IN_PROGRESS`。
- 执行日期：2026-08-03。

## 结论

S2-R5 的三轮有界 task-level 自适应约束尝试已完成，证据专项审计 `PASS / errors=0 / warnings=0`，但执行可行门槛未通过，结果标签为 `S2_R5_REQUIRES_ALGORITHM_CONSTRAINT`。Round1 将 q2 越限从 R4 的 `-0.10561825091356725 rad` 收窄到 `-0.027486350196529452 rad`；Round2/3 仍出现新的连续 branch 越限，Round3 的最小全身 clearance 进一步为 `0.0006595158746380083 m`，低于 `0.010 m`。没有裁剪输出、降低 gate、缩小 proxy/障碍或修改第三方算法。

## A：R4 收口

R4 failure acceptance 已完成并合并 PR #8。当前 R4 只有连续 q2 下界失败，q1/q3、方向、重复性和 full-body clearance 通过；根因记录在 `docs/evidence/S2-R4/root_cause/current_r4_q2_violation.json`，历史 R3 证据保持不变。

## B：R5 证据

- Round0：baseline 7 个 mode3；2000 Hz/adaptive 0.0005 s，2 个 q2 越限区间；q2 min `-0.10561825091356725`。
- Round1：新增 3、总数 10；区间 `4.0255 / 4.227 / 4.4435 s`；q2 min `-0.027486350196529452`；full-body `0.10536682251885507 m`，通过 clearance 但 joint fail。
- Round2：新增 3、总数 13；4 个新越限区间；q2 min `0.003636644695472535`，但 q1/q3 仍越界；full-body `0.04980180933033635 m`，通过 clearance 但 joint fail。
- Round3：新增 6、总数 19；5 个越限区间；q2 min `-0.003530976075788894`，q1 min `-0.10644131034309923`、q3 min `-0.02516776621502337`；full-body `0.0006595158746380083 m`，失败。
- 结论：固定 mode3 点的静态 margin 保持可行，但固定点之间的五次 arm polynomial 仍 overshoot；继续加点已达到本任务卡的三轮上限，不能代替连续算法约束。
- 分段边界：官方起终 arm state 在 `se3gcopter.h:934-943` 硬编码为 `[0,0,-boundArmZ]`，已写入 `PHASE_SPLIT_NOT_SUPPORTED_BY_OFFICIAL_ARM_ENDPOINT_CONTRACT`，未拼接分段轨迹。
- Nominal 轮次：Round1/2/3 均为真实 `capture_exit=0`，均有双轨迹；B6 的 smoke/loose/nominal repeat/narrow 未执行，因为最终 nominal 未通过 joint gate。
- 只读算法设计审计：已完成 `docs/evidence/S2-R5/algorithm_constraint_design/` 七份文件，推荐未来在官方 MINCO arm objective 的连续采样/梯度路径加入 Cartesian envelope barrier；未实现。

## 门槛与边界

最终 Round3：IK no-solution `0`；最大 FK residual `2.1516253669354347e-16 m`；q 范围 q1 `[-0.10644131034309923,0.49900160089863954]`、q2 `[-0.003530976075788894,0.4512970374167464]`、q3 `[-0.02516776621502337,0.4553330575531911]`；joint margin `-0.10644131034309923 rad`。100/200/400/800/2000 Hz 的 q2 min 与 FK residual 收敛证据在 `final_validation/frequency_convergence.json`。方向合同沿用已通过的 R4 P2→P3 水平 +x、P3→P4 水平 -x/+y，z direction error `4.163336342344337e-17 m`。

明确保持：未裁剪或投影输出轨迹；未缩小 body/rotor/link/EE proxy 或障碍；未降低 `0.010 m` clearance gate；未修改 AM-Planner 第三方源码、IK/FK、FlatnessMap、URDF/Xacro、ROS、Conda、GPU 或 checkpoint；未进入 S3/Isaac Lab；S2-R5 PR 不合并。

## 关键证据

- `docs/evidence/S2-R5/rounds/round_0..3/`
- `docs/evidence/S2-R5/runtime/round_1_nominal_abi_fixed_2/`
- `docs/evidence/S2-R5/runtime/round_2_nominal/`
- `docs/evidence/S2-R5/runtime/round_3_nominal/`
- `docs/evidence/S2-R5/phase_split_contract.md`
- `docs/evidence/S2-R5/algorithm_constraint_design/`
- `docs/evidence/S2-R5/final_validation/frequency_convergence.json`
- `docs/evidence/S2-R5/visuals/manifest.json`
- `docs/evidence/S2-R5/s2_r5_audit.json`
