# S2-R4 official mode contract

The task file and launch use the official mode vocabulary without changing the planner algorithm:

- mode 0: base guidance corridor before/after the crossarm task;
- mode 1: fixed base Cartesian point;
- mode 2: end-effector Cartesian/orientation/velocity/axis constraints, retained in the contract table for audit;
- mode 3: fixed base Cartesian plus fixed arm Cartesian point.

The real S2-R4 run uses one official mode-0 guide row and seven mode-3 base-plus-arm Cartesian rows, followed by an official mode-0 exit row. All mode-3 rows have the official 20-field shape. No mode-2 row was substituted for a mode-3 arm constraint, and no planner source or optimizer parameter was changed.
