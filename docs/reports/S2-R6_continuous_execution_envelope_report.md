# S2-R6 连续执行包络 barrier 报告

## 项目进度

- 正式阶段：2/9≈22%；本轮未进入后续正式阶段。
- 工程估算：本任务卡要求约33%的整体工程估算口径保持不变；本轮完成 S2-R5 收口和 S2-R6 证据包。
- S2 证据链：S2-R0～S2-R6 专项证据已生成；S2 仍为 `IN_PROGRESS`。
- 方法状态：`SUBMITTED_FOR_REVIEW`。

## 结论

S2-R5 的三轮有界 task-level 尝试已接受为失败证据并合并 PR #9。随后从最新 main 创建 S2-R6，在独立 WSL clone 中实现了默认关闭的 Cartesian execution-envelope barrier。Round1 disabled baseline 与历史 Round1 的 q、clearance 和双轨迹合同一致；`w0`、`10w0` 保持真实失败记录，`100w0` 首次同时通过 joint、full-body clearance 和 direction 硬门槛。结果标签为 `SUBMITTED_S2_R6_CONTINUOUS_ENVELOPE_READY`，等待负责人复核，不能写成 S2 PASS。

## A：S2-R5 收口

- `FAILURE_EVIDENCE_ACCEPTED`；Round1 q2_min=`-0.027486350196529452 rad`，Round2/3 的越界转移和 Round3 clearance 失败均保留。
- PR #9 已标记 Ready 并普通合并；merge commit/main Head：`f2d9fd3d2e0272fc0c392b8c11eede23f29b9f5b`。
- S2-R5 任务上限、官方 ABI、GPU、JPS/MINCO、双轨迹与历史 failure evidence 未被替换。

## B：S2-R6 实施与验证

### 源码与范围

- 独立 clone：`/home/amplanner/am-planner-s2-r6-ws/src/am-planner`，官方 commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。
- 允许的算法改动：`config.h`、`minco_arm.h`、新增 `execution_envelope_barrier.h`；另保留已接受的两个 S1 Python 3.9 CMake compatibility patch。
- 外部 clone diff patch SHA256：`3461c3119a390f73bc2ba545903297692db473d09272024b1327b8e0375f3288`。
- 新工作区 20 个 Catkin package 构建成功；GPU 为 RTX 5060 Ti，Python 3.9.23，Torch 2.7.1+cu128，CUDA 可用。
- 未改动 `se3gcopter.h`、`minco_base.h`、`plan_manage.cpp`、IK/FK、FlatnessMap、JPS、map/proxy、URDF/Xacro 或 ROS/GPU/overlay。

### 包络与 barrier

- 64 个有序 anchor balls，半径 `0.0015 m`；1,000,000 个固定种子 FK 样本、8 个角点和 36,000 个边界层样本全部通过官方执行分支 `[0, π/2]` 的 IK/FK 有限性检查。
- 每个 ball 内部 2000 点、边界 2000 点，全部 hard branch pass；中心 robust margin 最小约 `0.05 rad`。相邻 ball 全重叠，最大中心距 `0.0009841202645599642 m`，最小重叠余量 `0.002015879735440036 m`。
- Round1 固定点全部落入 balls；插值 corridor 的 `g_min=1.3211542975682412e-06 m²`。这是数值保守验证，不称形式化证明；原始 Round1 违反 polynomial 没有被重新标记为已覆盖。
- 公式：`z_i=r_i²-||p-c_i||²`，`g=τ log(mean(exp(z_i/τ)))`，`v=max(0,-g)`，`P_env=w_env v³`；使用稳定 log-sum-exp 和解析梯度，未在线有限差分或硬最近点切换。
- `τ0=2.2500000000000002e-07`；解析 Cartesian gradient 与中心有限差分最大绝对/相对误差均为 `1.45965e-18`；large-N 数学测试通过；非法 config 测试通过。
- MINCO 连续积分复用 `pos/vel/beta0/step/alpha/omg`，并保留原 workspace probability、velocity、extend 和 jerk 路径；ROS diagnostics 记录 `min g/active samples/max violation/barrier cost/integration samples`。

### 候选、正式包和消融

- `w0=861897036813.2117`：真实运行 `capture_exit=0`，但 q2_min=`-0.03879119402966391 rad`，失败。
- `10w0=8618970368132.117`：真实运行 `capture_exit=0`，但 q2_min=`-0.04632110053997662 rad`，失败。
- `100w0=86189703681321.17`：真实运行 `capture_exit=0`，通过 joint/clearance/direction，选为最终配置。
- smoke、loose、nominal repeat、narrow 均使用冻结的 100w0 配置真实运行，均 `capture_exit=0` 且硬门槛通过；narrow 未出现接口或数值错误。
- A0 disabled 与 A1 enabled 均为 Round1 task/map/proxy；A0 保留历史 q2 失败，A1 通过连续 joint gate、clearance 和 direction。两者的多速率与路径/jerk/cost 对比写入 `ablation.json`。

### 最终 100w0 输出

- 2000 Hz q_min=`[0.15798985216494277, 0.049664737476765364, 0.15798985216494277] rad`，q_max=`[0.31912040362251615, 0.3022411696556315, 0.3410338648190958] rad`；所有 q 仍在 `[0,π/2]`，最小 joint margin=`0.049664737476765364 rad`。
- IK no-solution=`0`；最大 FK residual=`1.8108188759524757e-16 m`；全身最小 clearance=`0.09210197487032999 m`，危险部件 `rotor_4`，发生时间约 `1.3675 s`；高于 `0.010 m` gate。
- direction error=`4.163336342344337e-17 m`，P2→P3 为水平 +x，P3→P4 为水平 -x/+y，合同通过。
- 官方日志诊断范围：75 条记录，`min_g=-0.000884905 m²`，最大 active samples=`2481`，最大 violation=`0.000884905 m²`，最大 barrier cost=`70780.7`，积分样本=`3589`；最终 cost=`3061.5`，规划时间=`150450 ms`，arm jerk=`0.17043677212987784`。官方日志未暴露可核验的 optimizer iteration count，因此不虚构迭代数；保留 `record_count=75`。
- 对最终导出的 arm trajectory 独立重算：`min_g=-1.4401189032693615e-05 m²`，active samples=`4954`，max violation=`1.4401189032693615e-05 m²`，`∫v³dt=9.375363981589439e-16`。
- nominal repeat 与 100w0 nominal 逐点 arm position 最大绝对差=`0 m`，q_min/clearance delta=`0`；100/200/400/800/2000 Hz 全部 finite、joint gate 和 full-body gate 通过。

## S2 readiness

专项审计为 `PASS / errors=0 / warnings=0`。S2 readiness 更新为 `NOT_READY_S2_R6_SUBMITTED_FOR_REVIEW`，因为 S2 仍在 `IN_PROGRESS`，S3-S8 仍冻结；Draft PR #10（`https://github.com/canimiliya/risk-aware-aerial-manipulation/pull/10`）不合并。

## 明确未执行

未添加 q ABI；未裁剪、饱和或 post-projection planner output；未替换 checkpoint；未缩小 proxy/障碍；未降低 `0.010 m` clearance gate；未实现 IK penalty；未修改 IK/FK/URDF；未进入 S3/Isaac Lab；未合并 S2-R6 PR。

## 证据

- `docs/evidence/S2-R6/source_manifest.json`
- `docs/evidence/S2-R6/envelope/`
- `docs/evidence/S2-R6/calibration.json`
- `docs/evidence/S2-R6/final_validation/`
- `docs/evidence/S2-R6/s2_r6_audit.json`
- `third_party/patches/AM-Planner_S2-R6_execution_envelope.patch`
