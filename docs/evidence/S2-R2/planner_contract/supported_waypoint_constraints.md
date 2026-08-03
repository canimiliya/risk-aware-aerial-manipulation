# Supported waypoint constraints

- `plan_manage.cpp:403-436` parses each `/task/inter_points` array as a numeric vector without named fields.
- `plan_manage.cpp:566-579` accepts only vector sizes `4`, `7`, `17`, or `20` according to the mode value in element zero.
- `se3_planner.cc:72-99` uses `segment(1, 3)` as the waypoint position; mode `2` may use `segment(4, 3)` as a direction/axis and a flag at element `7`.
- `se3_planner.cc:176-196` uses the mode-2 direction vector to form local approach/departure planes.
- `plan_manage.cpp:491-536` supports additional 4-vector pre/post position points.

This is a numeric waypoint/position/axis contract, not a Delta three-joint contract. The source does not document a named base-pose-plus-arm-q input.
