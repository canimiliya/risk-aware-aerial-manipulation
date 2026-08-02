# Fields unavailable from the current message/source contract

The following are intentionally not invented in the structured export:

- quaternion or full attitude trajectory;
- body yaw convention beyond the two scalar yaw fields;
- joint names, joint angles, joint velocities, or arm kinematic frame names;
- `phase_id`, semantic phase labels, contact state, or waypoint identifiers;
- planner cost, planning wall time, GPU utilization, or solver diagnostics as message fields;
- physical units for position coefficients (the message has no unit annotation; only ROS time handling and the observed `world` frame are recorded);
- an explicit “7 JPS segments” field or count. The write evidence is recorded as 19 polynomial segments; no unsupported JPS count is exported.
