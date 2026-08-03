# Official trajectory output contract

- `plan_manage.cpp:549-551` advertises `trajectory` and `trajectory_arm` as `quadrotor_msgs::PolynomialTrajectory`.
- `plan_manage.cpp:261-289` serializes polynomial coefficients and segment times.
- `quadrotor_msgs/msg/PolynomialTrajectory.msg:1-28` contains polynomial x/y/z coefficients, times, yaw endpoints, and metadata.
- `se3_planner.cc:48-53` runs the `SE3GCOPTER` MINCO path and produces `traj_` and `traj_arm_`.

The output contract is real ROS polynomial trajectories, but no runtime message was captured because the planner-contract gate failed before launch.
