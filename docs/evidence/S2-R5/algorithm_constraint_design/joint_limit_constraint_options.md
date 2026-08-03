# Joint-limit constraint options

## A. Cartesian execution-envelope barrier/penalty — recommended

Evaluate a conservative Cartesian envelope during `MINCO_S3_ARM::addTimeIntPenalty` and back-propagate its Cartesian gradient through the arm polynomial. This matches the existing differentiable workspace-penalty architecture and avoids adding an unsupported q field to the task ABI. Risk: the envelope approximation must be conservative and tested against official IK/FK.

## B. IK-based joint-bound penalty

Evaluate official IK at optimizer samples and penalize q outside the branch. This is direct but introduces branch selection, discontinuities near singular or multi-solution regions, and a difficult analytic derivative. It is a viable research option only with a defined differentiable branch and finite-difference/gradient checks.

## C. Post-projection

Project or clip the planner's Cartesian arm output into a feasible envelope after optimization. This is an anti-pattern for this gate: it changes the produced trajectory, breaks derivative/continuity claims, and cannot be reported as planner success. It is explicitly rejected.
