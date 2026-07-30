# BATCH-S0C-S1P：S0 正式收口与合并 + S1 AM-Planner 环境/源码只读预检

## 一、你的身份

你是一名负责 GitHub 工程治理、Windows/WSL 环境审计、ROS 科研复现准备、第三方源码静态审计和可复现证据管理的执行 Agent。

当前批次由两个有严格门槛的阶段组成：

```text
阶段 A：把已经通过高级总控审查的 S0 正式收口并合并 PR #1
        ↓ 只有 A 全部通过才允许继续
阶段 B：进入 S1 的只读预检，核验 WSL/Ubuntu 20.04/ROS Noetic 和 AM-Planner 源码条件
```

本轮不是 AM-Planner 正式安装任务，不运行官方规划示例，不下载 Polynomial_DiT checkpoint，不安装 ROS/CUDA/Isaac Lab，也不开始训练。

建议执行时长：45～90 分钟。

---

# 第一部分：权威上下文

## 1. 项目根目录

```text
D:\Desktop\my_project\Simulation_Research_on_Aerial_Manipulator_for_Power_Line_Bird_Diverter_Operation
```

## 2. GitHub 仓库

```text
https://github.com/canimiliya/risk-aware-aerial-manipulation.git
```

## 3. 当前 S0 PR

```text
PR：https://github.com/canimiliya/risk-aware-aerial-manipulation/pull/1
Base：main
Head：agent/s0-r1-workspace-hardware-audit
当前远端 Head：
2f441c4d4ebace01c3ef76cec00d546813dee267
状态：Open + Draft
```

## 4. 高级总控最终审查结论

高级总控已从 GitHub 核验以下证据：

- PR #1 真实 Head 为 `2f441c4d4ebace01c3ef76cec00d546813dee267`；
- 权威 S0-R1 任务卡为 27,587 bytes、1,056 lines、固定 SHA-256；
- `check_s0_structure.py` 为 `errors=0, warnings=0, exit_code=0`；
- 进度总控过期状态标记为 0；
- 硬件 JSON 顶层为 object；
- 中断文件完成仓库外备份和一致性重建；
- AM-Planner、Isaac Lab、Polynomial_DiT 许可证状态已分离记录；
- 未安装平台、未进入 S1、未训练。

正式审查结论：

```text
S0-R1-R2：PASS_WITH_LIMITATIONS
S0 阶段：PASS_WITH_LIMITATIONS
```

限制包括：

1. Isaac Sim/Isaac Lab 尚未安装或启动；
2. WSL 状态、Ubuntu 20.04 和 ROS Noetic 尚未完成最终可用性确认；
3. `LongPathsEnabled=0`；
4. 16 GB 显存后续需要 headless 和小并行实测；
5. AM-Planner、ROS、CUDA Toolkit、Polynomial_DiT 均未安装；
6. Polynomial_DiT 在冻结提交下无明确许可证，禁止公开再分发。

项目负责人已要求直接进入下一张任务卡，因此本轮获准完成 S0 状态收口和 PR #1 合并，并在成功后进入 S1 只读预检。

---

# 第二部分：总体安全规则

## 5. 禁止事项

本轮禁止：

1. 安装 ROS Noetic；
2. 安装 AM-Planner 的 Python、APT 或 Catkin 依赖；
3. 创建或修改 Conda 环境；
4. 安装 CUDA Toolkit；
5. 下载 Polynomial_DiT checkpoint；
6. 安装 Isaac Sim 或 Isaac Lab；
7. 修改 NVIDIA 驱动；
8. 修改 Windows 注册表或 Long Paths；
9. 创建、导入、删除或重置 WSL 发行版；
10. 执行 `wsl --unregister`、`wsl --shutdown`；
11. 修改已有 WSL 发行版中的软件包；
12. 运行 AM-Planner 正式规划任务；
13. 运行强化学习或长计算；
14. force push、rebase 或重写历史；
15. 跳过阶段 A 的合并门槛；
16. 将只读预检误报为“AM-Planner 已复现”。

允许：

- 读取本地和远端 Git 信息；
- 更新项目治理文档；
- 正常提交、推送和合并已批准的 PR #1；
- 启动 WSL 发行版执行只读命令；
- 使用受控超时；
- 执行 `git ls-remote`、`curl -I` 等网络探针；
- 在项目外临时目录做浅层/无 checkout 源码审计；
- 在 `third_party/am-planner/` 建立固定提交的源码工作副本，但不得安装依赖、下载模型或提交第三方源码到 Git；
- 创建审计脚本、报告和测试。

---

# 第三部分：阶段 A——S0 正式状态收口

## 6. A0：开始前 Git 和 PR 门槛

进入项目：

```powershell
$Root = "D:\Desktop\my_project\Simulation_Research_on_Aerial_Manipulator_for_Power_Line_Bird_Diverter_Operation"
Set-Location $Root

git fetch origin
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/agent/s0-r1-workspace-hardware-audit
gh pr view 1 --repo canimiliya/risk-aware-aerial-manipulation `
  --json state,isDraft,baseRefName,headRefName,headRefOid,mergeable,url
```

必须同时满足：

```text
工作树干净
当前分支：agent/s0-r1-workspace-hardware-audit
本地 HEAD：2f441c4d4ebace01c3ef76cec00d546813dee267
远端分支 HEAD：2f441c4d4ebace01c3ef76cec00d546813dee267
PR #1：Open
PR #1：Draft
Base：main
Head branch：agent/s0-r1-workspace-hardware-audit
PR Head SHA：2f441c4d4ebace01c3ef76cec00d546813dee267
PR 可合并
```

若 HEAD 漂移、工作树不干净或 PR 状态改变，停止并返回：

```text
BLOCKED_S0_CLOSEOUT_STATE_DRIFT
```

不得覆盖新修改。

---

## 7. A1：保存高级总控最终审查记录

新增：

```text
docs/reviews/S0_final_review_2026-07-31.md
```

至少包含：

```md
# S0 最终高级总控审查

- 审查对象：S0-R1-R2
- 审查 Head：`2f441c4d4ebace01c3ef76cec00d546813dee267`
- 审查结论：`PASS_WITH_LIMITATIONS`
- S0 阶段结论：`PASS_WITH_LIMITATIONS`

## 已通过

1. 独立 Git 工作区和 GitHub 事实源建立；
2. 硬件、驱动、磁盘和工具链审计；
3. AM-Planner 与 Isaac Lab 环境隔离合同；
4. 第三方 commit 与许可证风险记录；
5. 权威任务卡、报告和证据链恢复；
6. 自动检查 `errors=0, warnings=0`；
7. 中断文件无损备份和一致性重建。

## 限制

1. Isaac Sim/Lab 未安装和启动；
2. WSL、Ubuntu 20.04、ROS Noetic 仍需 S1 预检；
3. LongPathsEnabled=0；
4. 16 GB 显存需要后续 headless/小并行实测；
5. AM-Planner、ROS、CUDA Toolkit、Polynomial_DiT 未安装；
6. Polynomial_DiT 无明确许可证，禁止公开再分发。

## 权限

- 允许完成 S0 状态收口并合并 PR #1；
- 合并后允许进入 S1 只读预检；
- 不允许直接安装或执行 AM-Planner；
- 不允许长训练。
```

不得删改此前两次 `REVISION_REQUIRED` 审查记录。

---

## 8. A2：更新 S0 正式状态

### 8.1 进度总控 v1.2

修改：

```text
01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.2.md
```

将所有 S0 当前状态从：

```text
SUBMITTED_FOR_REVIEW
```

更新为：

```text
PASS_WITH_LIMITATIONS
```

当前任务槽位更新为：

```text
任务编号：S0-R1-R2
任务状态：PASS_WITH_LIMITATIONS
最终 commit：2f441c4d4ebace01c3ef76cec00d546813dee267
高级总控审查：PASS_WITH_LIMITATIONS
项目负责人决定：批准 S0 有限通过，允许完成状态收口并合并 PR #1
```

阶段总表：

```text
启动准备：PASS
S0：PASS_WITH_LIMITATIONS
S1：FROZEN（PR #1 合并后才允许切换为预检状态）
S2–S8：FROZEN
```

当前唯一下一步改为：

```text
提交 S0 正式审查记录
→ 运行回归检查
→ 将 PR #1 标记为 Ready
→ 使用 merge commit 合并 PR #1
→ 从合并后的 main 创建 S1 预检分支
```

不得把 Isaac Lab 或 AM-Planner 写成已可运行。

### 8.2 S0 状态页

更新：

```text
docs/milestones/S0_status.md
```

至少写为：

```text
S0-R1：REVISION_REQUIRED
S0-R1-R1：REVISION_REQUIRED
S0-R1-R2：PASS_WITH_LIMITATIONS
S0 正式阶段状态：PASS_WITH_LIMITATIONS
批准审查 Head：2f441c4d4ebace01c3ef76cec00d546813dee267
S1：等待 PR #1 合并后进入只读预检
允许长训练：否
```

### 8.3 决策日志

新增：

```text
D0026：高级总控最终审查 S0-R1-R2，结论 PASS_WITH_LIMITATIONS
D0027：项目负责人批准 S0 有限通过并完成 PR #1 合并
D0028：S1 首轮只执行 WSL/ROS/AM-Planner 源码预检，不安装依赖
```

均标记为 `ACTIVE`。

---

## 9. A3：更新 S0 检查器

当前 `scripts/audit/check_s0_structure.py` 仍检查“no approved S0”。S0 已经获得批准，因此必须更新为：

- 检查当前 S0 状态为 `PASS_WITH_LIMITATIONS`；
- 检查最终审查文件存在；
- 检查最终审查 Head 为 `2f441c4d...`；
- 检查限制条目仍存在；
- 检查 S1 尚未被写成已复现或已安装；
- 保留权威任务卡、JSON、许可证和敏感信息检查；
- 最终仍要求：

```text
errors=0
warnings=0
```

建议将输出保存到：

```text
docs/evidence/S0-FINAL/
```

至少包含：

```text
structure_check.txt
git_diff_check.txt
status_scan.txt
pr_premerge_snapshot.json
```

---

## 10. A4：回归检查

运行：

```powershell
python -m compileall scripts/audit
python scripts/audit/check_s0_structure.py
git diff --check
```

同时检查：

```powershell
git status --short
Get-ChildItem -Recurse -File | Where-Object Length -gt 10MB
```

复用敏感信息扫描。

必须达到：

```text
compileall exit=0
check_s0_structure exit=0
errors=0
warnings=0
git diff --check exit=0
无新增大文件
无凭据命中
```

---

## 11. A5：提交 S0 最终状态

提交：

```text
docs(s0): record approval and finalize milestone
```

推送：

```powershell
git push origin agent/s0-r1-workspace-hardware-audit
```

记录新的 PR Head：

```powershell
$S0FinalHead = git rev-parse HEAD
```

更新 PR #1 标题为：

```text
[S0] Initialize workspace and complete hardware/dependency audit
```

PR 正文必须写明：

```text
S0：PASS_WITH_LIMITATIONS
最终审查基准 Head：2f441c4d...
最新状态提交：<S0FinalHead>
自动检查：errors=0 warnings=0
限制：平台未安装、WSL/ROS 待预检、Long Paths=0、16 GB VRAM 待实测
下一步：合并后进入 S1 只读预检
```

---

## 12. A6：标记 Ready 并合并 PR #1

再次核验：

```powershell
gh pr view 1 --repo canimiliya/risk-aware-aerial-manipulation `
  --json state,isDraft,mergeable,headRefOid,baseRefName,headRefName
```

必须确认 PR Head 等于 `$S0FinalHead`。

然后：

```powershell
gh pr ready 1 --repo canimiliya/risk-aware-aerial-manipulation
```

使用普通 merge commit，保留所有 S0 历史：

```powershell
gh pr merge 1 `
  --repo canimiliya/risk-aware-aerial-manipulation `
  --merge `
  --match-head-commit $S0FinalHead
```

不得使用 squash、rebase、admin 强制或自动合并。

合并后核验：

```powershell
gh pr view 1 --repo canimiliya/risk-aware-aerial-manipulation `
  --json state,mergedAt,mergeCommit,headRefOid,url

git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
```

保存：

```text
docs/evidence/S0-FINAL/pr_merged_snapshot.json
docs/evidence/S0-FINAL/main_after_merge.txt
```

注意：若证据文件需要在合并后产生，不要回写已合并的旧分支。可在阶段 B 的新分支中保存最终合并快照。

### 阶段 A 失败门槛

以下任一发生，立即停止，不进入阶段 B：

```text
PR Head 漂移
检查失败
PR 无法 Ready
PR 无法正常 merge
main 无法 ff-only 同步
合并后的 main 不包含 S0 最终审查记录
```

状态：

```text
BLOCKED_S0_CLOSEOUT_OR_MERGE
```

---

# 第四部分：阶段 B——S1 环境与源码只读预检

只有阶段 A 全部通过后才允许执行。

## 13. B0：创建 S1 预检分支

确保当前位于合并后的 `main` 且工作树干净：

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
```

创建：

```powershell
git switch -c agent/s1-r0-environment-source-preflight
```

不得从旧 S0 分支创建。

---

## 14. B1：进度总控升级至 v1.3

将合并后的根目录：

```text
01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.2.md
```

原样移动到：

```text
docs/archive/01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.2.md
```

创建新的：

```text
01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.3.md
```

v1.3 保留完整协作合同，并更新：

```text
版本：v1.3
当前阶段：S1 AM-Planner 官方复现准备
总体状态：S1_PREFLIGHT_IN_PROGRESS
S0：PASS_WITH_LIMITATIONS
S1：IN_PROGRESS
当前任务：S1-R0
任务名称：WSL/ROS/AM-Planner 环境与源码只读预检
S2–S8：FROZEN
允许安装大型依赖：否
允许正式规划复现：否
允许长训练：否
```

更新 README 指向 v1.3。

不要删除 S0 的完整限制、审查和任务历史。

---

## 15. B2：创建 S1 预检证据结构

建立：

```text
docs/evidence/S1-R0/
docs/reports/S1-R0_preflight_report.md
docs/milestones/S1_status.md
docs/tasks/BATCH-S0C-S1P_任务卡.md
scripts/audit/s1_preflight.ps1
```

将本任务卡完整保存到 `docs/tasks/`，不得只保存摘要。

---

## 16. B3：Windows 和 WSL 宿主只读预检

创建受控 PowerShell 脚本，至少采集：

```powershell
wsl --version
wsl --status
wsl --list --verbose
wsl --list --running
```

每条命令使用合理超时，建议 30 秒，不得无限等待。

记录：

```text
命令
开始时间
结束时间
退出码
是否超时
stdout
stderr
```

如果 `wsl --status` 或 `wsl --version` 超时，但 `wsl --list --verbose` 可用，不得直接宣称 WSL 不可用，应分类记录。

不得执行 `wsl --shutdown`。

---

## 17. B4：逐个发行版只读识别

对以下实际存在的发行版逐个探针：

```text
Ubuntu-24.04
Ubuntu
NMPC-Ubuntu22
dbLaCAM-Ubuntu
AirFAR-Ubuntu20
```

使用受控命令：

```powershell
wsl -d <Distro> -- bash --noprofile --norc -lc "
set -o pipefail
echo '=== os-release ==='
cat /etc/os-release 2>/dev/null || true
echo '=== uname ==='
uname -a
echo '=== user ==='
id
echo '=== home ==='
printf '%s\n' \"\$HOME\"
echo '=== disk ==='
df -h / /home 2>/dev/null || true
echo '=== python ==='
python3 --version 2>&1 || true
echo '=== git ==='
git --version 2>&1 || true
echo '=== ros ==='
printf 'ROS_DISTRO=%s\n' \"\${ROS_DISTRO:-UNSET}\"
command -v roscore || true
command -v rosversion || true
test -d /opt/ros/noetic && echo NOETIC_DIR_PRESENT || echo NOETIC_DIR_ABSENT
dpkg-query -W ros-noetic-ros-base 2>/dev/null || true
echo '=== conda ==='
command -v conda || true
echo '=== project contamination clues ==='
find \"\$HOME\" -maxdepth 2 -type d \( -name '*am-planner*' -o -name '*Polynomial_DiT*' -o -name '*catkin*' \) 2>/dev/null | head -50
"
```

要求：

- 不使用 `sudo`；
- 不执行 `apt update`；
- 不 source 用户 shell 配置；
- 不修改任何文件；
- 单发行版建议 30～60 秒超时；
- 超时需记录，不得通过 `wsl --shutdown` 解决。

---

## 18. B5：候选 Ubuntu 20.04/ROS Noetic 策略判断

必须回答：

1. `AirFAR-Ubuntu20` 的实际 `VERSION_ID` 是否为 `20.04`；
2. 是否能稳定响应至少 3 次只读命令；
3. 是否已有 `/opt/ros/noetic`；
4. 是否已有 ROS Noetic 基础包；
5. 是否有既有项目或环境污染；
6. 可用磁盘是否足够；
7. 是否适合复用；
8. 若不适合，后续是否应新建独立 `AMPlanner-Ubuntu20` 发行版。

只允许以下策略结论之一：

```text
REUSE_AIRFAR_UBUNTU20_READ_ONLY_APPROVED_FOR_NEXT_INSTALL_TASK
CREATE_NEW_ISOLATED_UBUNTU20_RECOMMENDED
BLOCKED_WSL_UNRESPONSIVE
BLOCKED_NO_UBUNTU20_PATH
```

“复用批准”只表示下一轮可以设计安装任务，不表示本轮可安装。

原则上，若 `AirFAR-Ubuntu20` 已包含其他项目、环境复杂或用途不明，应优先推荐新建独立发行版，避免污染。

---

## 19. B6：AM-Planner 远程与源码冻结复核

固定仓库：

```text
https://github.com/SYSU-HILAB/am-planner.git
```

当前候选冻结 commit：

```text
7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d
```

先从 Windows 和候选 WSL 分别执行：

```text
git ls-remote <repo>
```

记录网络、DNS、TLS 和耗时。

### 19.1 本地源码副本

允许在：

```text
third_party/am-planner/
```

建立源码工作副本，但必须：

- 目录已被 `.gitignore` 忽略；
- 不提交第三方源码；
- 不递归下载模型；
- 不运行安装；
- 不修改第三方源码；
- 不执行 checkpoint 下载脚本。

推荐：

```powershell
git clone --filter=blob:none --no-checkout `
  https://github.com/SYSU-HILAB/am-planner.git `
  third_party/am-planner

Set-Location third_party/am-planner
git checkout --detach 7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d
git status --short
git rev-parse HEAD
```

如目录已存在，不得覆盖。先检查来源、commit 和工作树；来源不明则停止并报告。

### 19.2 静态源码审计

至少检查：

```text
README.md
LICENSE 是否真实存在
.gitmodules
requirements.txt
CMakeLists.txt
package.xml / 各 ROS package.xml
shfiles/setup.sh
shfiles/run.sh
shfiles/il.sh
src/plan/plan_manage/launch/run_in_sim_other.launch
src/plan/plan_manage/launch/tasks.yaml
Polynomial_DiT 的引用位置
checkpoint 下载脚本或 URL
官方可用任务列表
轨迹输出位置和格式线索
是否包含 Dockerfile/环境文件
```

不得只复述 README。必须通过源码回答：

1. 官方 `run.sh` 的三个选项分别是什么；
2. 哪些官方任务不需要 IL/checkpoint；
3. Basic planning 是否可在不下载 Polynomial_DiT 模型时运行；
4. IL-guided planning 的依赖和 checkpoint 入口；
5. 最小复现应先选哪 3 个官方任务；
6. 编译需要哪些 ROS package、APT 包、Python 包；
7. CUDA 11.8 是硬依赖还是仅 IL/学习模块建议；
8. 输出轨迹、日志和视频从哪里产生；
9. 是否使用 submodule、Git LFS 或额外私有资源；
10. README 声明 MIT 但 LICENSE 文件是否实际存在于冻结 commit；
11. 哪些依赖存在许可证或再分发风险；
12. 当前固定 commit 是否仍应作为 S1 正式复现 commit。

---

## 20. B7：Polynomial_DiT 只读依赖审计

固定：

```text
https://github.com/Dwl2021/Polynomial_DiT.git
commit：f31c8f04e5fa045bc08c7bbaaadfe60bb54816f1
```

本轮只允许：

```text
git ls-remote
读取 GitHub/源码树中的 README、requirements、download.py 和 checkpoint 入口
```

不得：

- 下载 checkpoint；
- 执行 `download.py`；
- 安装依赖；
- 将源码公开再分发；
- 把无许可证仓库当成 MIT。

必须回答：

1. checkpoint 来自何处；
2. 下载大小是否可推断；
3. 是否需要 Hugging Face、Google Drive 或其他服务；
4. 是否要求认证 token；
5. checkpoint 是否存在许可说明；
6. S1 基础规划复现是否可以暂时绕过该依赖；
7. 若必须使用，下一轮应采用何种隔离和证据方案。

---

## 21. B8：制定 S1 正式安装合同草案

新增：

```text
docs/environment_lock_s1_am_planner.md
```

必须明确但不执行：

```text
候选 WSL 发行版
Ubuntu 版本
ROS Noetic 安装方式
Python 3.8 环境名称
Conda/Mamba 策略
Catkin 工作区路径
AM-Planner 固定 commit
Polynomial_DiT 固定 commit
CUDA 是否需要
预计 APT 依赖
预计 Python 依赖
预计磁盘占用
模型下载策略
第三方源码位置
日志位置
失败回滚方式
是否允许复用现有发行版
```

必须区分：

```text
已验证事实
源码推断
下一轮待安装验证
```

不得把草案写成已安装状态。

---

## 22. B9：S1 预检自动检查

创建：

```text
scripts/audit/check_s1_preflight.py
```

至少检查：

- v1.3 当前进度文件存在；
- S0 为 `PASS_WITH_LIMITATIONS`；
- S1 为 `IN_PROGRESS` 或 `SUBMITTED_FOR_REVIEW`；
- S2–S8 为 `FROZEN`；
- WSL 命令证据存在；
- 每个发行版探针有退出/超时记录；
- 候选环境策略明确；
- AM-Planner commit 固定；
- AM-Planner 源码审计报告存在；
- Polynomial_DiT 未被误报为有许可证；
- 没有 checkpoint、大模型或大文件进入 Git；
- 没有安装成功的虚假声明；
- 没有敏感信息；
- 最终 summary 可输出：

```text
errors=0
warnings=<允许有明确限制，但不得有未解释错误>
```

如果存在 WSL 超时，允许作为记录完整的限制，不要求伪造为 0 warning；但每个 warning 必须有编号、证据和下一步。

---

## 23. B10：S1 预检报告

`docs/reports/S1-R0_preflight_report.md` 至少包含：

1. S0 合并后的 main commit；
2. 新分支基准；
3. WSL 宿主状态；
4. 各发行版实际版本；
5. AirFAR-Ubuntu20 是否可复用；
6. ROS Noetic 当前状态；
7. AM-Planner 网络和源码状态；
8. 固定 commit；
9. Basic 与 IL-guided 的依赖差异；
10. 推荐首批 3 个官方任务；
11. Polynomial_DiT/checkpoint 风险；
12. CUDA 是否为当前基础复现硬依赖；
13. 下一轮安装方案；
14. 明确未安装、未运行和未训练；
15. 阻断项；
16. 是否允许设计 S1-R1 正式安装任务。

---

## 24. B11：状态判定

只允许以下之一：

### `SUBMITTED_S1_PREFLIGHT`

满足：

- S0 已成功合并；
- WSL/发行版信息足以制定环境策略；
- AM-Planner 源码和网络可访问；
- 固定 commit 与依赖路径明确；
- 正式安装合同可制定；
- 未安装任何依赖。

环境策略可为“复用”或“新建独立 Ubuntu 20.04”。

### `BLOCKED_S1_WSL_UNRESPONSIVE`

WSL 无法获得足够证据，无法制定安全安装方案。

### `BLOCKED_S1_SOURCE_ACCESS`

AM-Planner 官方仓库或关键依赖无法访问，无法完成源码冻结。

### `BLOCKED_S0_CLOSEOUT_OR_MERGE`

阶段 A 未完成，不得进入阶段 B。

### `REVISION_REQUIRED`

执行了预检，但证据、脚本或状态不完整。

---

## 25. B12：提交和 Draft PR #2

任务完成后运行：

```powershell
python -m compileall scripts/audit
python scripts/audit/check_s0_structure.py
python scripts/audit/check_s1_preflight.py
git diff --check
```

提交建议：

```text
docs(s1): record AM-Planner environment and source preflight
```

如新增了通用审计脚本，可拆分：

```text
test(s1): add WSL and source preflight checks
docs(s1): record preflight evidence and environment contract
```

推送：

```powershell
git push -u origin agent/s1-r0-environment-source-preflight
```

创建 Draft PR #2：

```text
标题：
[S1-R0] AM-Planner environment and source preflight

Base：
main

Head：
agent/s1-r0-environment-source-preflight

Draft：
是
```

PR 正文必须包含：

- S0 merge commit；
- S1-R0 最终 commit；
- WSL 环境策略；
- AM-Planner 固定 commit；
- Basic/IL 依赖结论；
- 是否需要新建 Ubuntu 20.04；
- 未安装任何依赖；
- 请求高级总控审查。

---

# 第五部分：必须产出的关键文件

## 26. 阶段 A

```text
docs/reviews/S0_final_review_2026-07-31.md
docs/evidence/S0-FINAL/structure_check.txt
docs/evidence/S0-FINAL/git_diff_check.txt
docs/evidence/S0-FINAL/status_scan.txt
docs/evidence/S0-FINAL/pr_premerge_snapshot.json
```

合并后的最终 PR/main 快照可在 S1 分支中保存。

## 27. 阶段 B

```text
01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.3.md
docs/archive/01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.2.md
docs/tasks/BATCH-S0C-S1P_任务卡.md
docs/milestones/S1_status.md
docs/reports/S1-R0_preflight_report.md
docs/environment_lock_s1_am_planner.md
docs/evidence/S1-R0/
scripts/audit/s1_preflight.ps1
scripts/audit/check_s1_preflight.py
```

---

# 第六部分：最终回报格式

```text
1. 最终执行状态
SUBMITTED_S1_PREFLIGHT
或
BLOCKED_S0_CLOSEOUT_OR_MERGE
或
BLOCKED_S1_WSL_UNRESPONSIVE
或
BLOCKED_S1_SOURCE_ACCESS
或
REVISION_REQUIRED

2. 阶段 A：S0 收口
开始分支：
开始 HEAD：
状态提交：
S0 检查：
PR #1 Ready：
PR #1 是否合并：
PR #1 merge commit：
main 最终 commit：
S0 正式状态：

3. 阶段 B：S1 分支
分支：
基准 main commit：
最终 commit：
远端 commit：
Draft PR #2：
工作树：

4. WSL 宿主
wsl --version：
wsl --status：
发行版列表：
超时情况：

5. 发行版逐项结果
Ubuntu-24.04：
Ubuntu：
NMPC-Ubuntu22：
dbLaCAM-Ubuntu：
AirFAR-Ubuntu20：

6. AM-Planner 候选环境策略
REUSE_AIRFAR_UBUNTU20_READ_ONLY_APPROVED_FOR_NEXT_INSTALL_TASK
或
CREATE_NEW_ISOLATED_UBUNTU20_RECOMMENDED
或其他阻断状态
依据：

7. ROS Noetic
是否存在：
路径：
包状态：
是否可直接复用：
限制：

8. AM-Planner 源码审计
仓库：
冻结 commit：
源码副本路径：
LICENSE 文件：
run.sh 三个选项：
基础规划是否依赖 checkpoint：
推荐首批 3 个任务：
CUDA 是否为基础复现硬依赖：
额外资源：
轨迹输出线索：

9. Polynomial_DiT
冻结 commit：
许可证：
checkpoint 来源：
是否需要 token：
基础规划是否可绕过：
后续处理：

10. 自动检查
S0 regression：
S1 preflight check：
compileall：
git diff --check：
大文件：
凭据扫描：

11. 明确未执行
未安装 ROS：
未创建 Conda 环境：
未安装 CUDA：
未下载 checkpoint：
未运行规划：
未安装 Isaac Lab：
未训练：
未进入 S2：

12. 风险与阻断

13. 下一阶段建议
只判断是否允许设计 S1-R1 正式安装与官方基础示例复现任务，不得自行开始安装。
```

所有结论必须由命令、源码和 GitHub 证据支撑；不能只根据发行版名称、README 或旧聊天猜测。
