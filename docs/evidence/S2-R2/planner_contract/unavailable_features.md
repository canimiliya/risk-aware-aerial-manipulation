# Unavailable or unsupported features after the corrected contract

- Named Delta joint input (`m1_1,m2_1,m3_1`) in `tasks.yaml`: unavailable.
- Joint-vector output that can be independently mapped to official Delta FK: unavailable in the inspected ROS message contract.
- Dynamic base roll/pitch/yaw input: not present in the mode-2 start/end contract.
- A task schema combining dynamic base position, Delta q, and inter-points: unavailable.
- Exact tool 6D pose contract for the S2 crossarm tool: unavailable.

These are accepted S2-R2 limitations, not a planner-contract blocker. The old `BLOCKED_S2_R2_PLANNER_CONTRACT` label is preserved only in `final_acceptance/s2_r2_am_planner_audit.json` as historical correction evidence; the current label is `REVISED_S2_R2_PLANNER_CONTRACT`.
