# S3-R0 distance representation report

The former `|G1-G2| <= 0.002 m` gate is retired: G1 is an Isaac AABB-envelope
distance and G2 is a frozen S2 voxel/point-cloud distance. The diagnostic
`G1-G2` remains recorded; `geometry_representation_conservatism_m = G2-G1`
is positive when the AABB representation is more conservative.

- Point/AABB containment: **FAIL**, outside count `1`, max outside distance `0.0099999999999999672 m`.
- Point-cloud SHA unchanged: **True**.
- G1 minimum: `0.063242894273266487 m`, `rotor_4` vs `AdjacentObstacle` at `1.3708333333333333 s`.
- G2 minimum: `0.092717026502774455 m`, `rotor_4` at `1.3666666666666667 s`.
- G3 historical minimum: `0.092101974870329992 m`, `rotor_4`.
- Max `|G2-G3|`: `0.00061505163244446326 m`; max framewise `G1-G2`: `-0.0036407503283624187 m`.
- Representation effects are quantified per group in `s2_points_inside_s3_aabbs.json`; no AABB/point-cloud equivalence is claimed.

Overall decision: **FAIL**.
