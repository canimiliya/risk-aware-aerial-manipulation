# Supported waypoint constraints (corrected)

- `plan_manage.cpp:403-436` parses each `/task/inter_points` array as a numeric vector without named fields.
- `plan_manage.cpp:566-579` accepts only vector sizes `4`, `7`, `17`, or `20` according to the mode value in element zero.
- `se3gcopter.h:840-912` classifies element-zero type `0` as a guide point, types `1` and `3` as fixed base points, and type `3` additionally as a fixed arm Cartesian point from elements `4:7`.
- `se3_planner.cc:72-99,176-196` uses `segment(1, 3)` as the waypoint position; mode `2` uses element `7` as an axis-constraint switch and, when enabled, `segment(4, 3)` as the direction axis. The direction defines approach/departure planes; it is not a joint orientation input.
- `minco_base.h:543-550` uses mode `1/2` elements `4:7` and mode `3` elements `7:10` for the orientation penalty direction.

This is a numeric waypoint/position/axis/velocity/axis-fix contract, not a Delta three-joint contract. The source does not document a named base-pose-plus-arm-q input, and the absence of such a field is expected under the corrected official contract.
