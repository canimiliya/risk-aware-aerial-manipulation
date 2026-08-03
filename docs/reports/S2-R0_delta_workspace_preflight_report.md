# S2-R0 Delta 臂与横担工作空间预检报告（2026-08-03）

## 项目进度

- 开始总体进度：约 22%（按 S0–S8 九阶段等权的项目管理估算，S0 完成、S1 待收口前约 95%）。
- 结束总体进度：约 22%（按原任务卡口径，S0、S1 已收口；S2-R0 预检不折算为完整 S2 阶段完成度）。
- S1：`PASS_WITH_LIMITATIONS`。
- S2-R0：`PASS_WITH_LIMITATIONS`（最终收口审计通过；原始 `SUBMITTED_FOR_REVIEW` 预检证据保留）。

## G-ARM 结论

`G_ARM_READY_FOR_FULL_PLANNING`。标称暂定场景有满足水平候选轴、官方关节限位、暂定关节余量和代理 clearance 的 P0–P6 序列；它不是连续轨迹优化、动力学、碰撞 mesh 或 Isaac/PhysX 验收。

## 官方 Delta 模型

- 固定 AM-Planner commit：`7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。
- 主动关节：`m1_1`、`m2_1`、`m3_1`，均为 revolute，官方 URDF 限位 `[-1.57, 1.57] rad`；六个 trailing-arm 关节为初始化锁定值 0，不独立采样。
- 官方 launch/YAML 几何：static radius 0.08 m、moving/end-effector radius 0.025 m、upper arm 0.10 m、lower arm 0.16 m、scale 1.0。
- FK：逐项复用 `delta_display.cpp::FK_kin`；Jacobian：对该 FK 做中心有限差分，未把飞行器动力学 Jacobian 冒充为已验证模型。
- `B→A0` 安装：`[0,0,-0.05] m`、RPY `[0,0,-1.5708] rad`，来自官方 `ini_connect`。

## 场景合同

W、B、A0、E、T、C 的父子关系见 `docs/coordinate_frame_contract.md`。横担主梁、目标假件和一个邻近障碍仅为简化 AABB 代理；宽松/标称/狭窄尺寸全部标记 `PROVISIONAL_S2_ASSUMPTION`，不是现实电网尺寸。机体和旋翼也只使用半径代理，mesh/旋翼扫掠未执行。

## 工作空间采样

- 样本：100,000 个关节样本，随机种子 `20260803`，含 8 个角点边界样本；官方 FK 有效 90,205，闭链判别式无解样本 9,795，均保留而非掩盖。
- 末端位置范围（A0 frame）：min `[-0.15999997, -0.17455096, -0.25408624] m`；max `[0.15999871, 0.18450540, 0.04567495] m`。
- 全局 Jacobian：最小奇异值约 `9.016e-7`，条件数 P99 约 `401.50`；近奇异样本没有被删除。

## P0–P6 与敏感性

| 场景 | 可行数量 | 最小关节归一化余量 | 最小代理 clearance |
|---|---:|---:|---:|
| 宽松 | 7/7 | 0.40446 | 0.03373 m |
| 标称 | 7/7 | 0.40446 | 0.01627 m |
| 狭窄 | 0/7 | 0.40446 | -0.03321 m |

七个位姿依次为安全初始、外侧接近、水平伸入起点、抓取、直线拔出、反弹抑制缓冲和带载后撤。工具轴 `[1,0,0]` 仅是水平候选合同，来源为暂定假设；官方消息没有完整工具姿态字段。

## 主要瓶颈

标称场景的候选序列通过，但狭窄障碍代理使 clearance 失败；工作空间边界还出现近奇异样本。下一步完整规划必须重新定义真实场景尺寸、工具姿态/几何和连续轨迹碰撞/动力学门槛。

## 明确未执行

- 未修改官方 AM-Planner 算法 `.cpp/.h`、URDF/Xacro 或系统 ROS。
- 未更换机械臂、未下载 checkpoint、未运行 IL/Polynomial_DiT。
- 未运行 AM-Planner 连续全轨迹规划、Isaac Lab/PhysX、G-BRIDGE 或 S3。
- 未合并 S2-R0 Draft PR。
