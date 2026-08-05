# 决策日志

| ID | 日期 | 状态 | 依据 | 影响 | 重评条件 |
|---|---|---|---|---|---|
| D0001 | 2026-07-30 | ACTIVE | 采用纯仿真主线 | 排除真机为当前验收 | 项目负责人变更 |
| D0002 | 2026-07-30 | ACTIVE | AM-Planner 为名义规划候选 | 先规划后执行 | S1 复现失败 |
| D0003 | 2026-07-30 | ACTIVE | Isaac Lab 为候选动力学平台 | 统一接触/风扰接口 | S3 安装验证 |
| D0004 | 2026-07-30 | ACTIVE | 两平台离线文件连接 | 不建实时 ROS 桥 | 协议门槛 |
| D0005 | 2026-07-31 | ACTIVE | GitHub 为事实源 | 提交和审查可追溯 | 仓库变更 |
| D0006 | 2026-07-31 | ACTIVE | 高级总控审查、执行 Agent 实施、负责人决策 | 保持权限边界 | 负责人新授权 |
| D0007 | 2026-07-31 | ACTIVE | 每轮提交完整 SHA | 防止口头结论 | GitHub 审查 |
| D0008 | 2026-07-31 | ACTIVE | 先 S0 再 S1 | 禁止自动推进 | S0 审查 |
| D0009 | 2026-07-31 | PROPOSED | 仓库名 risk-aware-aerial-manipulation | 统一链接 | 负责人否决 |
| D0010 | 2026-07-31 | ACTIVE | 局部电网操作场景 | 限制研究范围 | 总纲修订 |
| D0011 | 2026-07-31 | ACTIVE | 轨迹协议先于控制学习 | 降低接口风险 | G-BRIDGE |
| D0012 | 2026-07-31 | ACTIVE | 硬件截图仅作线索，S0 必须命令核验 | 以 evidence 为准 | 新审计 |
| D0013 | 2026-07-31 | ACTIVE | 授权 S0-R1 | 允许初始化和审计 | 高级总控 |
| D0014 | 2026-07-31 | ACTIVE | 空仓库一次性最小 main 基线 | main 只含权威文件 | 审查批准 |
| D0015 | 2026-07-31 | ACTIVE | 实质修改必须在 agent 分支 | 防止 main 漂移 | 合并审批 |
| D0016 | 2026-07-31 | ACTIVE | 长路径只审计、不迁移 | 保留用户根目录 | 负责人授权 |
| D0017 | 2026-07-31 | ACTIVE | S0 禁止大型依赖和训练 | 控制风险和资源 | 新阶段授权 |
| D0018 | 2026-07-31 | PENDING | 项目 LICENSE 暂不决定 | 不误授许可证 | 负责人决定 |
| D0019 | 2026-07-31 | ACTIVE | 高级总控对 S0-R1 结论为 REVISION_REQUIRED | 触发返修 | 第二次审查 |
| D0020 | 2026-07-31 | ACTIVE | 项目负责人批准原分支 PR #1 执行 S0-R1-R1 | 限定返修范围 | 返修审查 |
| D0021 | 2026-07-31 | ACTIVE | 高级总控第二次审查 S0-R1-R1，结论 REVISION_REQUIRED | 触发最终收口 | 第三次审查 |
| D0022 | 2026-07-31 | ACTIVE | 项目负责人批准执行 S0-R1-R2 最终收口 | 限定治理收口范围 | 最终审查 |
| D0023 | 2026-07-31 | ACTIVE | 权威 S0-R1 任务卡固定二进制基准：27587 bytes、1056 lines、SHA-256 3EA65A31... | 可复核任务卡原件 | 基准变更须负责人授权 |
| D0024 | 2026-07-31 | ACTIVE | AM-Planner 许可证采用 README 声明与独立 LICENSE 文件可得性分离记录 | 避免不准确许可证陈述 | 再分发前复核 |
| D0025 | 2026-07-31 | ACTIVE | 电脑中断文件已仓库外备份并重建一致证据 | 保留中断历史和可复核恢复链 | 证据审查 |
| D0026 | 2026-07-31 | ACTIVE | 高级总控最终审查 S0-R1-R2，结论 PASS_WITH_LIMITATIONS | S0 可正式收口 | PR #1 合并失败或负责人撤销 |
| D0027 | 2026-07-31 | ACTIVE | 项目负责人批准 S0 有限通过并完成 PR #1 合并 | 允许使用普通 merge commit 合并 | 合并完成 |
| D0028 | 2026-07-31 | ACTIVE | S1 首轮只执行 WSL/ROS/AM-Planner 源码预检，不安装依赖 | 禁止安装、运行规划和训练 | S1-R0 审查 |
| D0029 | 2026-07-31 | ACTIVE | S1-R0 高级总控审查为 PASS | 允许正式收口并合并 PR #2 | 负责人撤销或合并失败 |
| D0030 | 2026-07-31 | ACTIVE | 正式环境不得复用 AirFAR-Ubuntu20 | 必须建立隔离 Ubuntu 20.04 发行版 | 新环境创建失败 |
| D0031 | 2026-07-31 | ACTIVE | 授权创建 AMPlanner-Ubuntu20 并安装 ROS Noetic/基础依赖 | 可进行受控环境搭建 | 任务边界变更 |
| D0032 | 2026-07-31 | ACTIVE | S1-R1 只复现 Basic，IL/Polynomial_DiT checkpoint 继续冻结 | 禁止 IL、checkpoint 与训练 | 后续明确批准 |
| D0033 | 2026-08-03 | ACTIVE | S1-R2 最终审查通过，S1 收口为 PASS_WITH_LIMITATIONS，PR #4 普通合并 | 允许进入受限 S2-R0 预检 | S1 审查撤销或证据失效 |
| D0034 | 2026-08-03 | ACTIVE | S2-R0 只读复用官方 Delta FK；横担/工具/机体代理参数单独标记 PROVISIONAL_S2_ASSUMPTION | 允许几何敏感性预检，不代表完整 S2 | 真实模型/场景合同核验 |
| D0035 | 2026-08-04 | ACTIVE | S1/S2-R0 审计改为默认无副作用，S2-R0 缺失 summary 从已提交 acceptance 语义恢复并保留 provenance；S2-R6 patch-only 复现和最终硬门槛全部通过 | S2 形成 PASS_WITH_LIMITATIONS 最终收口候选；S3 保持 NOT_STARTED，S4-S8 保持 FROZEN | PR #10 普通合并及负责人后续授权 |
| D0036 | 2026-08-05 | ACTIVE | 高级总控独立 final review 通过：S3 `PASS_S3_WITH_LIMITATIONS`，审查技术 Head `85bbb04ceefe5897826f6892fc9ff408b8cf0a5b`，PR #13 获准普通 merge | S3-R0 正式关闭，合并后正式进度为 `4/9≈44%`；S4–S8 继续 `FROZEN` | 负责人另行授权 S4 |
