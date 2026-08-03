# S2-R4 status

- S2-R4: `SUBMITTED_FOR_REVIEW`
- Result label: `SUBMITTED_S2_R4_JOINT_LIMIT_FAILED`
- S2: `IN_PROGRESS`
- S3-S8: `FROZEN`

The real official AMPlanner runs produced finite `/trajectory` and `/trajectory_arm` messages and passed the full-body proxy gate, direction contract, frequency convergence, and nominal repeatability. The independent official IK/FK execution contract still reports nominal `q2_min=-0.10561825091356725 rad`, so S2-R4 is not execution-feasible-ready. This is an accepted, reproducible failure result; no q clipping or proxy/obstacle relaxation was used.
