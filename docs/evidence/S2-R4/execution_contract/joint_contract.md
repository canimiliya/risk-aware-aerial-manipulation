# S2-R4 execution joint contract

- URDF mechanical limits remain the source mechanical envelope (`±1.57 rad` in the audited asset); they are not the execution gate.
- Official `DeltaDisplay::endCallback` publishes `q_i ∈ [0, π/2]`.
- Raw FK uses `theta_fk`; published joint state uses `q = π/2 - theta_fk`.
- Every sampled `/trajectory_arm` Cartesian point is evaluated with the official IK/FK pair. No q clipping, saturation, projection, or alternate IK branch is used.
- Hard gate: `min(q_i, π/2-q_i) >= 0`; preferred diagnostic margins: `0.02`, `0.05`, and `0.10 rad`.
- The current real S2-R4 runs fail this hard execution gate in nominal/repeat (`q2_min=-0.10561825091356725 rad`), while FK residual and IK finiteness remain valid.
