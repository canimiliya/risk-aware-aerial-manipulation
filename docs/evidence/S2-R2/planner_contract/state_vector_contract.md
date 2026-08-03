# Official state-vector contract

- `plan_manage.cpp:458-459` initializes base start/end state matrices as `3x3`.
- `plan_manage.cpp:466-473` fills only the first column with base `x,y,z`; no roll, pitch, yaw, or arm-joint fields are loaded.
- `se3_planner.h:31-33` exposes `MatDf init_state_, fin_state_` and `:59-60` passes them to `Setup`.
- `plan_manage.cpp:142-147` calls `Setup(init_state_, fin_state_, mode_, inter_info_)`.

The official input can express a base position and intermediate position/axis constraints, but it cannot express the required pair `(dynamic base position, Delta q[3])` as an auditable task input. A dynamic W→B trajectory cannot be reconstructed from this contract without inventing unsupported fields.
