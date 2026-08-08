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
