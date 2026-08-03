# S2-R2 AM-Planner 横担连续规划报告

## 结论

本轮已纠正旧的 planner-contract 判断，并完成真实 AM-Planner 横担规划证据；结果为 `SUBMITTED_S2_R2_AM_PLANNER_READY`，提交复核，不等同于 S2 总体 PASS。

旧的 `BLOCKED_S2_R2_PLANNER_CONTRACT` 是历史合同误判：官方接口确实不接收 Delta `q[3]`，但 AM-Planner 的 arm 本来就是内部 Cartesian `MINCO_S3_ARM` 优化变量，官方输出是 `/trajectory_arm` Cartesian polynomial。该历史状态、失败运行和原始日志均未覆盖或删除。

## 结果摘要

| 场景 | 真实运行 | 双轨迹 | 100 Hz 代理最小 clearance | 100 Hz base 路径长度 | 结论 |
|---|---:|---:|---:|---:|---|
| smoke_free | 是 | `/trajectory` + `/trajectory_arm` | base 0.1833 m / arm 0.0630 m | 5.7289 m | PASS |
| loose | 是 | `/trajectory` + `/trajectory_arm` | base 0.0243 m / arm 0.0595 m | 6.0367 m | PASS |
| nominal | 是 | `/trajectory` + `/trajectory_arm` | base 0.0515 m / arm 0.0497 m | 7.5745 m | PASS |
| nominal repeat | 是 | `/trajectory` + `/trajectory_arm` | base 0.0515 m / arm 0.0497 m | 7.5745 m | PASS |
| narrow diagnostic | 是 | `/trajectory` + `/trajectory_arm` | base 0.0166 m / arm 0.0644 m | 6.1802 m | PASS，诊断场景 |

所有原始消息的 390 个数值字段均有限，NaN/Inf 均为 0；五次运行均有非零 base 与 arm Cartesian 轨迹。nominal 与 repeat 的 100 Hz 端点差为 0，消息合同一致；100/200/400 Hz 均由同一原始消息独立重采样并保存。

## 合同与证据

- 官方源：`third_party/am-planner`，commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。
- base 边界：`init_state_`/`fin_state_` 为 `3x3`，第一列为位置，零边界列对应速度/加速度。
- mode 0/1/2/3 合同：`4/7/17/20`；机器可读版本见 `docs/evidence/S2-R2/planner_contract/inter_info_contract.json`。
- arm 内部链：`iArmSta_`、`fArmSta_`、`innerPA_`、`dimArmP_`、`MINCO_S3_ARM`、`armOpt_`；没有新增任务字段，没有伪造 q[3]。
- 运行目录：`docs/evidence/S2-R2/runtime/`；导出目录：`data/trajectories/S2-R2/100Hz`、`200Hz`、`400Hz`；独立验证：`docs/evidence/S2-R2/validation/real_run_validation.json`。

## 限制

点云 clearance 是由实际发布地图点生成的球形 proxy 检查，不是 mesh/实体碰撞证明。ROS `PolynomialTrajectory` 不携带原始 mode-2 direction flag/vector，因此 direction error 只报告“未编码”，没有从轨迹反推或虚构数值。`/trajectory_arm` 没有被冒充为 Delta 关节轨迹，故本轮不声明 IK、关节限位或动力学全验收。

S2 保持 `IN_PROGRESS`，S3-S8 保持 `FROZEN`。本轮等待项目负责人复核后再推进。
