# S2-R4 status

- S2-R4: `FAILURE_EVIDENCE_ACCEPTED`
- Result label: `SUBMITTED_S2_R4_JOINT_LIMIT_FAILED`
- S2: `IN_PROGRESS`
- S3-S8: `FROZEN`

The real official AMPlanner runs produced finite `/trajectory` and `/trajectory_arm` messages and passed the full-body proxy gate, direction contract, frequency convergence, and nominal repeatability. The independent official IK/FK execution contract still reports nominal `q2_min=-0.10561825091356725 rad`, so S2-R4 is not execution-feasible-ready. The failure evidence is accepted and reproducible; no q clipping or proxy/obstacle relaxation was used. The current R4 q2 entry/minimum/exit records are in `docs/evidence/S2-R4/root_cause/current_r4_q2_violation.json`.
