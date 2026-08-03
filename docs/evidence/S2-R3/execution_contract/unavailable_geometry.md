# S2-R3 尚不可得的几何

- 官方 URDF 命名了 `drone.dae` 和 Delta mesh，但本项目不提交第三方完整 mesh；未能从现有 ROS runtime 取得可复用的 rotor center/radius 参数。
- 因此 body、rotor center/radius 和 upper/lower capsule radius 均明确保留来源标签 `PROVISIONAL_S2_ASSUMPTION`；结果称为 full-body proxy，不称为 mesh 精确碰撞。
- tool 的真实长度和末端完整 mesh 未在 `PolynomialTrajectory` 合同或本轮可复用输入中给出，列为 accepted limitation。
