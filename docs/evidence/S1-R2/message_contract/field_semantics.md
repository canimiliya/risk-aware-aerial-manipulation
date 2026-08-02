# `quadrotor_msgs/PolynomialTrajectory` field semantics

The contract is taken from the message definition and the fixed-source consumers:

- `header`: ROS Header. The captured messages use `frame_id=world`; the message itself does not prescribe a universal frame.
- `trajectory_id`: uint32 trajectory identifier; the planner source increments a local counter.
- `action`: uint32 command. The source sets `ACTION_ADD` when publishing the planned trajectory; abort/warning constants are also defined.
- `num_order`: present in the message but the captured planner leaves it at `0`; it is not used as the per-segment order in the source exporter.
- `num_segment`: number of polynomial pieces.
- `start_yaw`, `final_yaw`: scalar yaw endpoints. Captured planner messages contain `0.0`; no yaw unit is encoded in the message.
- `coef_x`, `coef_y`, `coef_z`: flattened per-axis normalized position coefficients. For segment `i`, exactly `order[i] + 1` entries are consumed, in the source's descending-power matrix column order.
- `time`: positive segment durations. The source accumulates these as ROS seconds.
- `mag_coeff`: time scaling divisor used by the trajectory server; captured messages use `1.0`.
- `order`: per-segment polynomial order. The captured four runs contain order `5` for every segment.
- `debug_info`: free-form source string; captured messages are empty.

Base and arm messages have the same ROS message type and fields. Their distinction is the topic (`/trajectory` versus `/trajectory_arm`) and the planner publication path; the message has no joint-name or body/arm schema field.
