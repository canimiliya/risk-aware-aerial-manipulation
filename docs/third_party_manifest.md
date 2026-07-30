# 第三方引用冻结（S0）

查询日期：2026-07-31；均未克隆、未安装、未下载 checkpoint。

| 项目 | 官方仓库 | 冻结引用 | 许可证验证 | 风险 |
|---|---|---|---|---|
| AM-Planner | SYSU-HILAB/am-planner | main/HEAD `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d` | `LICENSE_NOT_FOUND_OR_NOT_VERIFIED` | ROS/Ubuntu/依赖与 checkpoint 待 S1 核验 |
| Isaac Lab | isaac-sim/IsaacLab | v2.3.2 `37ddf626871758333d6ed89cf64ad702aef127d0` | `LICENSE`, SHA256 `DF351EBFA8AF317BF5A9AD83DF63A8B68E4F5C04B71F30767CDB27AA434EAC62` | RTX 50/驱动兼容性和平台安装待后续批准 |
| Polynomial_DiT | Dwl2021/Polynomial_DiT | main/HEAD `f31c8f04e5fa045bc08c7bbaaadfe60bb54816f1` | `LICENSE_NOT_FOUND_OR_NOT_VERIFIED` | checkpoint 获取和依赖待 S1 |

AM-Planner 在 S1 开始前重新核验 main；Isaac Lab 固定 v2.3.2，不跟随开发分支。
