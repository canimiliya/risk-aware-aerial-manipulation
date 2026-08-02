# Polynomial order and coefficient convention

Source evidence:

- `plan_manage.cpp::TrajToMsg` pushes each segment's `normalizePosCoeffMat()` columns from `j=0` through `j=order`.
- `trajectory.h::normalizePosCoeffMat` scales the coefficient columns by powers of segment duration.
- `traj_server.cpp` evaluates `beta0 = [u^5,u^4,u^3,u^2,u,1]` for order 5, and uses `beta1`, `beta2`, `beta3` with duration, duration² and duration³ divisors.

Therefore this exporter evaluates each axis as:

```text
p(u) = c[0] u^order + c[1] u^(order-1) + ... + c[order]
u = local_segment_time / segment_duration
```

The first three derivatives are exported because the fixed source explicitly computes position, velocity and acceleration. Jerk is source-computable too, but is not exported in this contract because the current exporter only promises fields independently sampled and validated in its CSV/NPZ schema; the raw message remains authoritative.
