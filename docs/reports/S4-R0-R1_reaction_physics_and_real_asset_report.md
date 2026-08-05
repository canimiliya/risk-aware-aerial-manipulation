# S4-R0-R1 反作用物理修正与真实资产绑定报告

## 结论

当前标签：`BLOCKED_S4_R0_VISUAL_EVIDENCE_INCOMPLETE`。

反作用公式、质量来源、质量记账、240 Hz 动力学与审计已完成；真实 S3 USD 已按固定 SHA 作为视觉副本的来源并建立 `/World/RobotVisual` 合同。但在当前 Isaac Sim 5.1 native runtime 中，该资产的自定义 STL 显示层在加载后逐帧改 root/time code 时触发原生退出，R1 尚未形成 12 张 PNG、3 段视频和 3 张曲线，因此不能提交 READY。

## 反作用修正

旧公式把 `velocity / dt` 当成加速度，首帧会产生虚假脉冲。新接口明确接收 `q, dq, qdd`，使用：

```text
v_com = J(q) dq
a_com = J(q) qdd + Jdot(q,dq) dq
```

模型范围标记为 `COM_TRANSLATIONAL_ONLY`，不保留未使用的转动惯量参数。静止 `q/dq/qdd` 的力和力矩为 0；高精度数值差分验证通过；所有反作用有限。

## 质量来源与记账

来源：`D:/i3/a/aerial_manipulator_v2.usd`，SHA-256 为 `74cce4b4cd8a41da9b60829482debbf3a78c0548bacb9dd53089e92c5ed7bc7d`。USD MassAPI 读回 10 个非零刚体，机械臂总质量 `0.29135232232511044 kg`，每个刚体的质量、COM、对角惯量和 prim path 已写入 preflight provenance。

质量合同为 `BASE_PLUS_ARM_SEPARATE`：

```text
base_mass = 0.98 kg
arm_mass = 0.29135232232511 kg
total_system_mass = hover_feedforward_mass = 1.27135232232511 kg
arm gravity = explicit downward load on the dynamic base, balanced by total hover feedforward
```

## 动力学结果

- gravity drop：z 从 `2.4998298 m` 降至 `1.2429239 m`，末速度 `-4.9458714 m/s`。
- hover_hold：3/3，position RMSE `0.00113662 m`。
- initial offset recovery：4/4，position settling `0.4875–0.75 s`。
- arm_motion_hold reaction ON：3/3，base RMSE `0.00117217 m`，joint RMSE `0.0100401 rad`，反作用峰值 `2.91867 N / 0.475650 Nm`。
- reaction OFF 对照：1/1；ON/OFF 均保留。
- minimum clearance 全部约 `0.7726 m` 以上。
- collision disabled，所以 `physics_contact_available=false`、`physics_contact_count=null`；安全字段是 `sampled_proxy_clearance_only`，没有把 null 伪装为 0。

旧错误公式重算对比已写入 `r1_correction_comparison.json`：arm run01 旧/新 force peak 为 `6.61975/2.91867 N`，force RMS 为 `0.557297/0.0793499 N`，torque peak 为 `1.07635/0.475650 Nm`。

## 视觉限制

视觉合同记录：source USD、SHA、`/World/RobotVisual`、`/World/QuadrotorBase`、active/passive joint 顺序和 visual-only physics isolation。当前尝试的 real Isaac GUI state replay 已保留日志，但 native runtime 在 asset reference 加载后的时间采样/逐帧 root 更新阶段退出；因此新 R1 visual manifest 尚未生成，旧 S4-R0 视觉证据保持不覆盖。

## 状态

`S4=IN_PROGRESS`，`S4-R0=SUBMITTED_FOR_REVIEW`，正式进度仍 `4/9≈44%`；完整闭链动力学和完整 nominal trajectory closed loop 均为 false；S5–S8 冻结。PR #14 必须继续保持 Draft、Open、未合并。

## 验证记录

- R1 定向套件：`18 passed`；状态写入审计：`pass=true`，记录 `22571`，reset 后 root/joint 写入均为 `0`；名义控制审计通过 `3/4/3` 组运行。
- 完整 pytest：`79 passed, 13 failed`。13 个失败均来自既有 S0/S1/S2 审计输入缺失或冻结 S3 点云/manifest 哈希漂移；没有修改这些历史证据，也没有把它们重标为本轮通过。
