# S4-R0 status

## Current state

- S4: `IN_PROGRESS`
- S4-R0: `SUBMITTED_FOR_REVIEW`
- Formal progress: `4/9≈44%` (unchanged during R0)
- S5–S8: `FROZEN`
- Authorization: project owner explicitly authorized S4 on 2026-08-05.

## Scope

This milestone establishes the first nominal, no-wind dynamic closed-loop demonstration: hover hold, recovery from small reset offsets, and arm motion while the base remains controlled. It does not close S4, and it does not start wind, contact, training, the full AM-Planner trajectory closed loop, or S5.

## Acceptance status

`SUBMITTED_FOR_REVIEW`, with the R2 readiness gate currently blocked:
`BLOCKED_S4_R0_R2_NATIVE_VISUAL_PIPELINE_UNRESOLVED`. The analytic reaction
correction, MassAPI provenance, mass accounting, dynamic runs, and directed
tests remain unchanged and pass. R2's independent P0-P3 matrix reaches the
native viewport/link-update failure, and the flattened visual cache fails the
standard-Mesh and physics-schema gates. No R2 PNG/video/curve manifest is
promoted; the prior S4-R0 visual evidence is preserved and explicitly remains
legacy. S4 stays open and independent final review remains pending.

## R2 evidence

- crash matrix: `docs/evidence/S4-R0/visuals/r2/visual_crash_matrix.json`
- cache audit: `docs/evidence/S4-R0/visuals/r2/visual_cache_manifest.json`
- honest visual manifest: `docs/evidence/S4-R0/visuals/r2/s4_r0_r2_visual_manifest.json`
- base/head pytest comparison: `docs/evidence/S4-R0/tests/base_vs_head_pytest.json`

## S4-R3 asset gate

S4-R3 is blocked at the authoritative USD topology gate:
`BLOCKED_S4_R3_DELTA_TOPOLOGY_UNRESOLVED`. The source has 10 positive-mass
arm links, 3 active-joint candidates and 6 passive-joint candidates, but zero
existing loop joints and no floating UAV base. No native runtime, viewport,
video, rotor, wind, contact, full trajectory or S5 work was started.

## S4-R4 RRRP native dynamics gate

R3 的 Delta 路线在本轮停止，旧 `aerial_manipulator_v2.usd` 保持只读；活动机械臂切换为独立的 RRRP serial articulation。`rrrp_design.yaml` 是唯一设计事实源，当前为 `ENGINEERING_NOMINAL` 且 `provisional=true`。

R4 资产与运行时证据已生成：3 个 revolute + 1 个 prismatic、4 DOF、总 arm mass 0.63 kg、最大几何伸展 0.47 m；固定基座和浮动基座各完成 2000 physics steps，q1/q2/q3/P effort response、浮动基座自然反作用、P=0/middle/max 和状态写入审计均通过。线动量最大相对漂移为 `2.2777646545515437e-06`，低于 1% 门槛。

R4 readiness：`S4_R4_RRRP_NATIVE_DYNAMICS_READY`。该标签只表示 R4 RRRP 原生动力学门通过；`FULL_ROTOR_ACTUATION=false`、`HARDWARE_PARAMETER_VALIDATED=false`、`CONTACT_DYNAMICS_VALIDATED=false`、`S4_READY=false`，因此不得据此进入 R5。
