# S2-R5 algorithm constraint design: insertion points

This is a read-only design audit after the three bounded task-level rounds. No third-party source is changed.

- `third_party/am-planner/src/plan/traj_opt/include/se3gcopter/se3gcopter.h:618-669` maps the optimizer vector into base time/position and arm free-point variables, calls `forwardPA`, generates the arm MINCO trajectory, and evaluates the arm cost and gradient.
- `se3gcopter.h:1129-1155` performs the first constrained L-BFGS stage and regenerates the arm trajectory from the optimized arm variables.
- `third_party/am-planner/src/plan/traj_opt/include/se3gcopter/minco_arm.h:258-323` is the existing arm trajectory cost path and workspace-probability gradient path.
- `minco_arm.h:355-378` contains the existing differentiable workspace penalty integration over each polynomial segment.

The smallest future implementation insertion point is inside `MINCO_S3_ARM::addTimeIntPenalty`, immediately beside the existing workspace penalty, so the penalty is evaluated on the same polynomial samples and contributes an analytic Cartesian gradient. A second insertion point is the call site in `SE3GCOPTER::objectiveFunc`; it should remain a call-through, not a post-processing projection.

This audit does not authorize implementation in S2-R5.
