# S2-R3 轨迹回放合同

- `traj_server.cpp:698-771` 和 `773-839`：分别接收 `/trajectory` 与 `/trajectory_arm` 的 `PolynomialTrajectory`，保存 `time/order/coef_x/y/z/mag_coeff`。
- `traj_server.cpp:450-538`：按段定位时间，使用归一化五阶 basis `beta0..beta3`，生成 position/velocity/acceleration/jerk；arm z 再限制到 `[-0.23,-0.06]`。
- `traj_server.cpp:538-590`：base 同样生成四阶导数输入，并固定 `yaw=0`、`yaw_dot=0.01`。
- wrapper 不改 ROS 消息、不改官方源码，800 Hz 只表示离线重采样；`qdot/qddot` 仅为数值导数。
