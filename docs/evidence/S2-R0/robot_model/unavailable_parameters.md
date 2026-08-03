# 未可证明的官方参数

- 真实电力横担/导线/绝缘子尺寸：官方 AM-Planner 源码未提供，不能从任务图或经验猜成官方值。
- 机体外壳、旋翼半径、旋翼平面和完整 mesh 几何用于 clearance：源码含 mesh 路径，但本轮不把 mesh 尺寸解读成物理包络；使用 `collision_proxy_contract.json` 中的暂定代理。
- `E→T` 工具轴、工具长度、夹具接触面和抓取姿态：现有 ROS 轨迹消息与 Delta FK 源码没有完整任务工具合同。
- `W→B` 动态安装位姿、风场、质量/惯量耦合和完整 Jacobian：本轮只对官方闭链位置 FK 做有限差分 Jacobian，不声称完成飞行器-机械臂动力学。
- 侧向障碍位置和三组宽松/标称/狭窄尺寸：均为 `PROVISIONAL_S2_ASSUMPTION`，只用于几何敏感性预检。
