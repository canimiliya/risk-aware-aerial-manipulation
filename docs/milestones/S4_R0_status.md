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

`SUBMITTED_FOR_REVIEW`, with the R1 readiness gate currently blocked:
`BLOCKED_S4_R0_VISUAL_EVIDENCE_INCOMPLETE`. The analytic reaction correction,
MassAPI provenance, mass accounting, dynamic runs, and directed tests pass.
However, the current Isaac native runtime exits while time-sampling the S3
custom-STL visual layer, so the new R1 PNG/video/curve manifest has not been
generated. The prior S4-R0 visual evidence is preserved and not overwritten;
independent S4 final review remains pending.
