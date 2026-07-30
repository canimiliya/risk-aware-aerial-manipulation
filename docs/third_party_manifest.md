# 第三方引用与许可证冻结

查询日期：2026-07-31；均未完整克隆、未安装、未下载 checkpoint。

| 项目 | 官方仓库/冻结引用 | 许可证核验 | 证据/风险 |
|---|---|---|---|
| AM-Planner | SYSU-HILAB/am-planner；main/HEAD `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d` | `LICENSE_NOT_FOUND_OR_NOT_VERIFIED`；冻结根目录无 LICENSE，README 未给明确许可证 | contents API、README URL；不因许可证不明取消主线 |
| Isaac Lab | isaac-sim/IsaacLab；v2.3.2 `37ddf626871758333d6ed89cf64ad702aef127d0` | `BSD-3-Clause`，原文已保存 | `third_party/licenses/isaaclab_LICENSE_v2.3.2.txt`；SHA-256 `EE11EA20952B1682AD42BE520D8931020E611E41F5336D33939E7CF3FFD0217E` |
| Polynomial_DiT | Dwl2021/Polynomial_DiT；main/HEAD `f31c8f04e5fa045bc08c7bbaaadfe60bb54816f1` | `NO_EXPLICIT_LICENSE_FOUND_AT_FROZEN_COMMIT` | `third_party/licenses/Polynomial_DiT_LICENSE_STATUS_f31c8f0.md`；禁止公开再分发源码/checkpoint |

AM-Planner 在 S1 开始前再核验；Isaac Lab 固定 v2.3.2；Polynomial_DiT 许可证澄清前仅作为依赖风险记录。
