# S3-R0 status

- S3：`SUBMITTED_S3_R0_FK_FAILED`
- 轨迹协议：`PASS`
- Isaac Sim/Isaac Lab 基础运行：`READY_WITH_LIMITATIONS`
- 机器人导入与场景加载：`PASS_WITH_LIMITATIONS`
- 播放：`PASS_RUNTIME / FK_FAILED`
- 接触与 clearance：`NOT_EXECUTED`
- S4--S8：`FROZEN`

本轮保留了旧 pip-only/flatdict 失败现场，并改用官方 Isaac Sim 5.1 pip package → Isaac Lab v2.3.2 官方源码 → `isaaclab.bat -i none`。新环境可导入并完成 Isaac Sim empty-stage/PhysX 10-step smoke，官方 AM-Planner Delta 资产也已导入 USD；名义轨迹完整播放 1046 帧，但关节回读和项目 FK 残差超过硬门槛，接触查询与 clearance 尚未执行。因此不宣称 S3 PASS，也不进入 S4。
