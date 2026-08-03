# S2-R4 failure review — 2026-08-03

## Decision

`FAILURE_EVIDENCE_ACCEPTED`

The S2-R4 result is a valid, reproducible execution-gate failure. The real official AM-Planner/ROS/GPU capture is retained. Independent official IK/FK evaluation at 2000 Hz with 0.0005 s adaptive resolution reports two q2-underflow intervals and a nominal minimum of `q2=-0.10561825091356725 rad`. No output clipping, saturation, projection, proxy shrinkage, obstacle change, clearance relaxation, or algorithm-source modification was used.

## Evidence distinction

- Historical S2-R3 had multiple q1/q2/q3 branch violations and full-body collision failures.
- Current S2-R4 passes the required runtime contracts, direction contract, nominal repeatability, frequency checks, and full-body proxy clearance. It fails only the continuous official joint-limit gate because q2 leaves `[0, pi/2]`.
- The 500,008-sample static arm envelope and selected P0–P6 points are feasible; therefore the observed failure is a trajectory-level failure between fixed task points, not evidence that the selected static points are infeasible.

## Gate record

| Check | Result |
|---|---|
| Real smoke/loose/nominal/repeat/narrow capture | Captured; required four variants have exit 0 and JPS/MINCO/GPU/dual topics |
| IK no-solution | 0 |
| Nominal 800 Hz q2 minimum | `-0.10561825091356725 rad` |
| Nominal 2000 Hz q2 minimum | `-0.10561825091356725 rad` |
| Nominal max FK residual | `1.5170650228460041e-16 m` |
| Nominal full-body clearance | `0.13274285460118745 m`, gate `0.010 m` passed |
| Direction | Passed; P2→P3 +x horizontal and P3→P4 -x,+y horizontal |
| Repeatability | q path and clearance deltas 0; same dangerous component |
| Algorithm/geometry boundary | Official algorithm and obstacle/proxy/gate retained |

## State

`S2-R4: FAILURE_EVIDENCE_ACCEPTED`
`S2: IN_PROGRESS`
`S3–S8: FROZEN`

The acceptance closes the evidence review only. It does not mark S2-R4 execution-feasible-ready and does not authorize S2 or S3 advancement.
