# Validation plan for a future algorithm constraint

1. Unit-test the Cartesian barrier and analytic gradient against finite differences.
2. Re-run the unchanged official R4 baseline to prove no environment or proxy drift.
3. Run nominal once and independently validate at 100/200/400/800/2000 Hz with adaptive 0.0005 s sampling.
4. Require IK no-solution=0, finite FK residual, q in [0,pi/2], no branch jump, q margin sensitivity at 0.02 and 0.05, and qdot/qddot diagnostics.
5. Re-run full-body clearance for body, rotors, upper arms, lower rods, platform, and EE at >=0.010 m; verify direction and repeatability.
6. Only after nominal passes, run smoke, loose, nominal repeat, and narrow under the task-card time limits.
