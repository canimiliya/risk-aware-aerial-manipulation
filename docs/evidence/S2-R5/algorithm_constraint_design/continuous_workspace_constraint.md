# Continuous workspace/joint constraint design

The failure pattern is between fixed Cartesian mode-3 points: Round1 reduced q2 overshoot, while Round2 and Round3 moved the polynomial into new branch violations. Fixed-point feasibility is therefore not a continuous execution constraint.

Recommended future design: sample every arm polynomial segment at the existing integration nodes, compute a smooth Cartesian feasible-envelope barrier, and integrate it with the existing workspace penalty. The barrier should use the fixed full-body proxy and the same 0.010 m execution gate in validation; it must not change the proxy or gate. A differentiable soft barrier can be paired with a hard post-optimization validator that rejects any non-finite or out-of-range trajectory.

The barrier must cover the Delta joint branch through a conservative Cartesian envelope with targets corresponding to q1,q3>=0.02, q2>=0.05, and q<=pi/2-0.02. Those values are design targets, not a license to clip the output. The output trajectory must remain the optimizer's trajectory and be independently revalidated.
