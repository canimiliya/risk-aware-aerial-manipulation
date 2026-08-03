# Official state-vector contract (corrected)

Source checkout: `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`.

- `plan_manage.cpp:458-459` initializes `init_state_` and `fin_state_` as `3x3` matrices.
- `plan_manage.cpp:466-473` fills the first column with base `x,y,z`; the remaining zero columns represent boundary velocity and acceleration. This is the official base position/velocity/acceleration boundary representation, not a 3-element pose vector.
- `se3_planner.h:31-33,59-60` carries the matrices to `SE3GCOPTER::setup`.
- `se3gcopter.h:58-70,939-950` keeps arm boundary matrices internally as `iArmSta_`/`fArmSta_`, initializes their first column to `(0,0,-boundArmZ)`, and optimizes arm Cartesian variables through `MINCO_S3_ARM`, `innerPA_`, `dimArmP_`, and `armOpt_`.

The corrected contract therefore has one official base boundary object (`3x3`, position/velocity/acceleration columns) and internal Cartesian arm optimization variables. There is no explicit task field for Delta `q[3]`, `m1_1/m2_1/m3_1`, or a joint-vector trajectory input. The earlier blocker wording that treated missing `q[3]` as a failure of the AM-Planner contract was a contract misjudgment and is retained only in the historical audit/run evidence.
