# S2-R3 官方 FlatnessMap 姿态合同

- `flatness.h:34-135`：`FlatnessMap::forward(vel,acc,jer,psi,dpsi,thr,quat,omg)`。
- `delta_display.cpp:205-252`：`posCmdCallback` 从 `PositionCommand` 读取 velocity/acceleration/jerk/yaw/yaw_dot，调用 `flatness.forward`，再写入 quadrotor quaternion、odometry 和 body angular velocity。
- 项目 wrapper 逐项保留官方 drag、gravity、tilt quaternion 和 angular-rate 公式；输出 quaternion 顺序为官方内部 `w,x,y,z`，转换为 `R_WB` 后检查有限性、归一化、正交性和 `det(R)=+1`。
- 这只是官方执行层映射和离线 playback，不是闭环飞控、姿态跟踪或电机动力学证明。
