# Gradient and differentiability requirements

The official optimizer already computes polynomial position, velocity, and acceleration at integration nodes and accumulates `gdC`/`gdT` in `minco_arm.h:258-461`. A future continuous constraint should use the same nodes and chain rule through `beta0` into the 6-by-3 coefficient block.

Required checks before implementation acceptance:

1. finite analytic gradient for every active sample;
2. directional finite-difference agreement on representative interior and near-boundary points;
3. no branch switching in the differentiable evaluation path;
4. finite cost and gradient under all three arm components and at segment boundaries;
5. no change to the official task ABI, proxy geometry, obstacle set, clearance gate, or endpoint contract.

If official IK is used for option B, the branch must be frozen for a local derivative test and the non-differentiable branch-transition cases must be separately rejected by validation.
