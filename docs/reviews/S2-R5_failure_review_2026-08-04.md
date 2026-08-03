# S2-R5 failure review — 2026-08-04

## Decision

`FAILURE_EVIDENCE_ACCEPTED`

S2-R5 is a valid bounded failure of task-level fixed-point adaptation. Three real official AM-Planner runs retained the official mode-3 ABI, GPU workspace model, JPS/MINCO path, and both trajectory topics. The fixed mode-3 points remained statically feasible, while the continuous arm polynomial still left the official execution joint branch between points.

## Accepted facts

- Round0 retained the baseline 7 mode-3 points and measured `q2_min=-0.10561825091356725 rad`.
- Round1 added 3 points, reached 10 total, improved `q2_min` to `-0.027486350196529452 rad`, and passed the `0.010 m` full-body clearance gate, but still failed the continuous joint gate.
- Round2 added 3 points, reached 13 total, made `q2_min=0.003636644695472535 rad`, but transferred the continuous violation to q1/q3.
- Round3 added 6 points, reached 19 total, still failed the joint gate and also failed full-body clearance with minimum `0.0006595158746380083 m` at `rotor_1`.
- All three real runs had `capture_exit=0`, official GPU/JPS/MINCO logs, and `/trajectory` plus `/trajectory_arm` evidence. Direction validation passed for every round.
- The failure is between fixed points in the fifth-order arm polynomial; it is not evidence that the selected fixed points are statically infeasible.
- The three-round task-level budget is exhausted. Adding more fixed points is no longer an adequate substitute for an algorithm-level continuous constraint.

## Integrity boundary

No q clipping, saturation, post-projection, proxy shrinkage, obstacle/map change, clearance-gate relaxation, checkpoint replacement, or third-party algorithm modification was used in S2-R5. The read-only algorithm design audit recommends a future Cartesian execution-envelope barrier in the official MINCO arm continuous-integral path; that algorithm patch belongs to S2-R6 and is not part of this acceptance.

## State

`S2-R5: FAILURE_EVIDENCE_ACCEPTED`
`S2: IN_PROGRESS`
`S3–S8: FROZEN`

This acceptance closes the S2-R5 evidence review only. It does not mark S2 ready and does not authorize S3.

## Evidence

- `docs/reports/S2-R5_adaptive_task_constraints_report.md`
- `docs/evidence/S2-R5/s2_r5_audit.json`
- `docs/evidence/S2-R5/rounds/round_0/round_summary.json`
- `docs/evidence/S2-R5/rounds/round_1/round_summary.json`
- `docs/evidence/S2-R5/rounds/round_2/round_summary.json`
- `docs/evidence/S2-R5/rounds/round_3/round_summary.json`
- `docs/evidence/S2-R5/final_validation/frequency_convergence.json`
- `docs/evidence/S2-R5/phase_split_contract.md`
