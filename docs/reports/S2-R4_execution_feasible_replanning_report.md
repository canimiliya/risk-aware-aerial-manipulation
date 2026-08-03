# S2-R4 execution-feasible constrained replanning report

## Conclusion

S2-R4 is accepted as failure evidence under `FAILURE_EVIDENCE_ACCEPTED` with result label `SUBMITTED_S2_R4_JOINT_LIMIT_FAILED`. The task-level constrained replan reached the real official AMPlanner execution layer: smoke-free, loose, nominal, and nominal-repeat all returned `capture_exit=0`, used GPU/JPS/MINCO, and emitted finite non-empty base and arm trajectories. The fixed full-body proxy passed in nominal (`0.13274285460118745 m` minimum, rotor_4), but the official execution joint contract did not: nominal and repeat have `q2_min=-0.10561825091356725 rad`. Therefore S2 remains `IN_PROGRESS`; S3-S8 remain `FROZEN`.

## Root cause and preserved boundaries

The S2-R3 raw evidence was independently accepted before this branch. Its nominal 800 Hz trajectory had q violations in insert, pull/buffer, and return, with the historical body proxy failure preserved. S2-R4 static envelope sampling used 500,000 seeded samples plus 8 boundary corners. P0-P6 all have static `q ∈ [0, π/2]`, preferred margin at least `0.18 rad`, and static proxy clearance above `0.010 m`. The real planner's Cartesian polynomial nevertheless leaves the feasible q branch near the approach/entry and produces a negative q2 during the nominal run; this is a planner/constraint expressiveness failure, not an IK implementation failure.

The official asset search did not find authoritative body/rotor dimensions that replace the existing provisional proxy. The body `0.20 m`, rotor disk radius `0.25 m`, existing rotor centers, official joint-point centerlines plus existing capsules, platform/EE `0.025 m`, and clearance gate `0.010 m` were retained. Obstacles, target task positions, planner core, optimizer weights, JPS parameters, ROS, GPU, and mechanical arm were not changed.

## Real planner and independent validation

The task was one official mode-0 guide / seven mode-3 fixed base-plus-arm Cartesian rows / one mode-0 exit row. The logs contain JPS path search, MINCO setup and finish, CUDA workspace initialization, and trajectory publication. Both `/trajectory` and `/trajectory_arm` were non-empty with 570 finite numeric fields and zero NaN/Inf in each successful required run.

Nominal 800 Hz independent recomputation: 3,991 samples, IK no-solution `0`, maximum FK residual `1.5170650228460041e-16 m`, q range `q1 [0.15798985216494277, 0.49398934058058774]`, `q2 [-0.10561825091356725, 0.30085766289705607]`, `q3 [0.15798985216494277, 0.32077532006315046]`, minimum joint margin `-0.10561825091356725 rad`. Flatness remained finite with quaternion norm error `1.11e-16`, rotation orthogonality error `3.43e-16`, determinant minimum `0.9999999999999997`, positive thrust, and finite omega.

Nominal full-body minimum clearance was `0.13274285460118745 m` at `1.1825 s`, most dangerous component `rotor_4`; the `0.010 m` gate passed. Frequency runs at 100/200/400/800 Hz and adaptive 2,000 Hz converged to the same joint-limit failure, while nominal/repeat raw q paths and clearance values were exactly identical (`max q-path delta=0`, clearance delta `0`). Direction passed: P2→P3 horizontal +x; P3→P4 horizontal −x,+y, with z direction error `4.163336342344337e-17 m`.

## Review result and next boundary

The dedicated S2-R4 audit has `decision=PASS`, `errors=[]`, `warnings=[]`; this means the evidence package is complete and the failed gate is preserved, not that S2-R4 passed. The failure review is `docs/reviews/S2-R4_failure_review_2026-08-03.md` and the formal acceptance is `docs/evidence/S2-R4/final_review/s2_r4_failure_acceptance.json`. The only next permitted research action is an explicitly authorized task-level constraint/waypoint redesign or algorithm-level constraint work under a new task card. This report does not authorize S3, Isaac Lab, IL, or Polynomial_DiT.

Evidence: `docs/evidence/S2-R4/validation/s2_r4_execution_validation.json`, `docs/evidence/S2-R4/final_acceptance/s2_r4_execution_feasible_audit.json`, `docs/evidence/S2-R4/root_cause/`, `docs/evidence/S2-R4/arm_envelope/`, `docs/evidence/S2-R4/static_feasibility/`, `docs/evidence/S2-R4/runtime/`, and `docs/evidence/S2-R4/visuals/`.
