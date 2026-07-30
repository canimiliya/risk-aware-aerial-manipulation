# BATCH-S1R0C-S1R1：S1-R0 收口合并与 AM-Planner 隔离环境安装、构建及三项基础示例复现

## 一、执行身份

你是一名负责 Windows/WSL、ROS Noetic、Catkin、C++/Python 依赖管理、无人机轨迹规划源码复现和科研证据治理的执行 Agent。

本任务不是只给安装建议。你必须直接读取本地项目、执行命令、建立隔离环境、安装依赖、构建固定源码、运行官方基础示例、保存原始证据并提交 GitHub。

本批次分为两个有严格门槛的阶段：

```text
阶段 A：正式记录 S1-R0 审查通过并合并 PR #2
        ↓ 只有阶段 A 全部成功才允许继续
阶段 B：创建全新隔离 Ubuntu 20.04 WSL
        ↓
阶段 C：安装 ROS Noetic、构建工具和 Python 3.8 环境
        ↓
阶段 D：克隆并构建固定 commit 的 AM-Planner
        ↓
阶段 E：依次运行 grasp、other/write、other/lift 三项基础任务
        ↓
阶段 F：形成可复现脚本、证据、报告和 Draft PR #3
```

预计执行时间：60～150 分钟。网络或 APT 较慢时允许更长，但不得无限等待。

---

# 第二部分：权威上下文与已批准结论

## 1. 项目根目录

```text
D:\Desktop\my_project\Simulation_Research_on_Aerial_Manipulator_for_Power_Line_Bird_Diverter_Operation
```

## 2. GitHub 仓库

```text
https://github.com/canimiliya/risk-aware-aerial-manipulation.git
```

## 3. 当前 S1-R0 PR

```text
PR：https://github.com/canimiliya/risk-aware-aerial-manipulation/pull/2
Base：main
Head：agent/s1-r0-environment-source-preflight
当前 Head：
9b5ae4657571f5821a2f806f736f2fb29f11731a
状态：Open + Draft
```

## 4. S0 基线

```text
S0：PASS_WITH_LIMITATIONS
PR #1 merge commit：
58724118d4f857dc0b3bd23c4d415e70219b853e
```

## 5. 高级总控对 S1-R0 的审查结论

```text
S1-R0：PASS
S1 阶段：IN_PROGRESS
允许完成 PR #2 状态收口并普通 merge
允许创建一个新的隔离 Ubuntu 20.04 WSL 发行版
允许在该新发行版中安装 ROS Noetic、构建工具和 AM-Planner 基础依赖
允许构建固定 commit 并运行三项不使用 IL/checkpoint 的官方基础任务
```

已核验事实：

1. PR #2 的 Head 为 `9b5ae4657571f5821a2f806f736f2fb29f11731a`；
2. WSL 宿主命令可用；
3. `AirFAR-Ubuntu20` 实际为 Ubuntu 20.04.6，已有 ROS Noetic，但属于既有项目环境；
4. 环境策略为 `CREATE_NEW_ISOLATED_UBUNTU20_RECOMMENDED`；
5. AM-Planner 固定 commit 为 `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`；
6. Polynomial_DiT 固定 commit 为 `f31c8f04e5fa045bc08c7bbaaadfe60bb54816f1`；
7. `run.sh` 三项入口为 grasp、strike、other；
8. 基础规划入口不调用 Polynomial_DiT checkpoint，IL 路径由 `il.sh` 单独启动；
9. 本轮推荐复现 grasp、other/write、other/lift；
10. ROS Noetic 已于 2025-05-31 EOL，但官方说明二进制仍保留在 `packages.ros.org`。本任务必须记录这一限制，不得将其描述为仍受官方维护。

---

# 第三部分：本轮明确授权和边界

## 6. 本轮明确允许

仅允许：

1. 更新 S1-R0 状态和审查记录；
2. 将 PR #2 标记 Ready 并使用普通 merge commit 合并；
3. 创建一个新 WSL 发行版：

```text
AMPlanner-Ubuntu20
```

4. 其安装位置优先固定为：

```text
D:\WSL\AMPlanner-Ubuntu20
```

5. 在该新发行版内部安装 Ubuntu/ROS/构建/Python 依赖；
6. 新建用户 `amplanner`；
7. 为该隔离本地研究环境配置仅限该用户的 passwordless sudo；
8. 在该发行版内创建：

```text
/home/amplanner/am-planner-ws
```

9. 克隆 AM-Planner 固定 commit；
10. 安装不含 IL/checkpoint 的基础依赖；
11. Catkin 构建；
12. 运行三项基础示例；
13. 创建可复现脚本和测试；
14. 在失败时保留新发行版和日志用于诊断。

## 7. 本轮禁止

1. 修改或删除 `AirFAR-Ubuntu20`；
2. 修改其他 WSL 发行版；
3. 执行 `wsl --unregister`；
4. 执行 `wsl --shutdown`；
5. 修改 Windows 注册表；
6. 修改 NVIDIA 驱动；
7. 安装 Windows 侧 CUDA Toolkit；
8. 安装 Isaac Sim 或 Isaac Lab；
9. 下载 Polynomial_DiT checkpoint；
10. 运行 `shfiles/il.sh`；
11. 安装或启用完整 torch/torchvision/triton IL 栈，除非基础构建经源码证据证明无法绕过且高级总控另行批准；
12. 修改 AM-Planner 核心算法；
13. 为了编译通过静默改写第三方源码；
14. 复用 `AirFAR-Ubuntu20` 作为正式环境；
15. 进入 S2；
16. 训练任何模型；
17. 合并本轮最终 Draft PR #3；
18. 删除失败日志；
19. 将“ROS 节点启动”误报为“轨迹规划成功”。

---

# 第四部分：阶段 A——S1-R0 正式收口并合并 PR #2

## 8. A0：状态漂移检查

进入项目目录：

```powershell
$Root = "D:\Desktop\my_project\Simulation_Research_on_Aerial_Manipulator_for_Power_Line_Bird_Diverter_Operation"
Set-Location $Root

git fetch origin
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/agent/s1-r0-environment-source-preflight

gh pr view 2 `
  --repo canimiliya/risk-aware-aerial-manipulation `
  --json state,isDraft,baseRefName,headRefName,headRefOid,mergeable,url
```

必须同时满足：

```text
工作树干净
当前分支：agent/s1-r0-environment-source-preflight
本地 HEAD：9b5ae4657571f5821a2f806f736f2fb29f11731a
远端 Head：9b5ae4657571f5821a2f806f736f2fb29f11731a
PR #2：Open + Draft
Base：main
Head branch：agent/s1-r0-environment-source-preflight
PR Head：9b5ae4657571f5821a2f806f736f2fb29f11731a
PR 可合并
```

任何一项不符，停止并返回：

```text
BLOCKED_S1_R0_STATE_DRIFT
```

不得覆盖新的修改。

## 9. A1：保存高级总控审查记录

新增：

```text
docs/reviews/S1-R0_review_2026-07-31.md
```

至少包含：

```md
# S1-R0 高级总控审查

- 审查 Head：`9b5ae4657571f5821a2f806f736f2fb29f11731a`
- 结论：`PASS`
- S1 阶段：`IN_PROGRESS`

## 已通过

1. WSL 宿主和五个发行版只读探针完整；
2. AirFAR-Ubuntu20 已确认是 Ubuntu 20.04.6 和 ROS Noetic 环境；
3. 正式策略选择新建隔离 Ubuntu 20.04，避免污染旧环境；
4. AM-Planner 和 Polynomial_DiT 固定 commit；
5. Basic 与 IL/checkpoint 路径完成分离；
6. 推荐三项基础任务；
7. 自动检查 errors=0、warnings=0；
8. 未安装依赖、未运行规划。

## 允许的下一步

- 合并 PR #2；
- 创建 `AMPlanner-Ubuntu20`；
- 安装 ROS Noetic 和基础构建依赖；
- 构建固定 AM-Planner commit；
- 运行 grasp、other/write、other/lift；
- IL/checkpoint 继续冻结。
```

## 10. A2：更新 v1.3 和 S1 状态

在当前 v1.3 中：

```text
S1-R0：PASS
当前任务：S1-R0
任务状态：PASS
高级总控审查：PASS
最终 commit：9b5ae4657571f5821a2f806f736f2fb29f11731a
```

S1 阶段保持：

```text
IN_PROGRESS
```

下一任务写为：

```text
S1-R1：隔离环境安装、构建与三项基础示例复现
```

更新：

```text
docs/milestones/S1_status.md
docs/decision_log.md
```

新增决策：

```text
D0029：S1-R0 高级总控审查为 PASS
D0030：正式环境不得复用 AirFAR-Ubuntu20
D0031：授权创建 AMPlanner-Ubuntu20 并安装 ROS Noetic/基础依赖
D0032：S1-R1 只复现 Basic，IL/Polynomial_DiT checkpoint 继续冻结
```

## 11. A3：回归检查、提交与合并

运行：

```powershell
python -m compileall scripts/audit
python scripts/audit/check_s0_structure.py
python scripts/audit/check_s1_preflight.py
git diff --check
```

必须全部退出 0。

提交：

```text
docs(s1): approve environment and source preflight
```

推送：

```powershell
git push origin agent/s1-r0-environment-source-preflight
```

记录：

```powershell
$S1R0FinalHead = git rev-parse HEAD
```

更新 PR #2 标题：

```text
[S1-R0] Approve AM-Planner environment and source preflight
```

PR 正文至少包含：

```text
S1-R0：PASS
审查基准：9b5ae465...
状态提交：<S1R0FinalHead>
环境策略：CREATE_NEW_ISOLATED_UBUNTU20_RECOMMENDED
下一步：新建隔离 WSL、安装、构建和三项基础复现
```

标记 Ready：

```powershell
gh pr ready 2 --repo canimiliya/risk-aware-aerial-manipulation
```

使用普通 merge commit：

```powershell
gh pr merge 2 `
  --repo canimiliya/risk-aware-aerial-manipulation `
  --merge `
  --match-head-commit $S1R0FinalHead
```

禁止 squash、rebase 和 admin 强制。

合并后：

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
```

记录 merge commit 为 `$S1R0MergeCommit`。

若合并失败，不得进入后续阶段，返回：

```text
BLOCKED_S1_R0_MERGE
```

---

# 第五部分：阶段 B——创建全新隔离 Ubuntu 20.04 WSL

## 12. B0：创建 S1-R1 分支

必须从合并后的干净 main 创建：

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main

git switch -c agent/s1-r1-am-planner-install-basic-repro
```

不得从旧 S1-R0 分支创建。

## 13. B1：保存本任务卡和建立证据目录

建立：

```text
docs/tasks/BATCH-S1R0C-S1R1_任务卡.md
docs/evidence/S1-R1/
docs/reports/S1-R1_install_build_reproduction_report.md
docs/milestones/S1_R1_status.md
scripts/setup/
scripts/reproduce/
```

将本任务卡完整保存，不得摘要。

## 14. B2：安装前门槛

运行并保存：

```powershell
wsl --version
wsl --help
wsl --list --online
wsl --list --verbose
Get-PSDrive D
Test-Path "D:\WSL\AMPlanner-Ubuntu20"
```

必须确认：

```text
不存在已注册的 AMPlanner-Ubuntu20
D:\WSL\AMPlanner-Ubuntu20 不存在，或存在但为空且明确属于本轮
在线列表包含 Ubuntu-20.04，或官方 Ubuntu 20.04 下载入口可访问
D 盘至少有 30 GB 空闲
当前 WSL 支持 WSL2
```

若同名发行版或非空目录已存在，停止并返回：

```text
BLOCKED_S1_R1_EXISTING_DISTRO_OR_DIRECTORY
```

不得覆盖。

## 15. B3：首选官方安装方式

如果 `wsl --help` 显示支持：

```text
--name
--location
--no-launch
--web-download
```

且 `wsl --list --online` 包含 `Ubuntu-20.04`，首选执行：

```powershell
New-Item -ItemType Directory -Force -Path "D:\WSL" | Out-Null

wsl --install Ubuntu-20.04 `
  --name AMPlanner-Ubuntu20 `
  --location "D:\WSL\AMPlanner-Ubuntu20" `
  --no-launch `
  --web-download
```

所有 stdout、stderr、退出码和耗时保存到：

```text
docs/evidence/S1-R1/wsl_install/
```

如果命令明确提示参数组合不支持，不得反复盲试，进入 B4 的官方离线导入回退。

如果命令要求重启 Windows，停止并返回：

```text
BLOCKED_S1_R1_REBOOT_REQUIRED
```

不得声称安装完成。

## 16. B4：官方 Ubuntu 20.04 Appx 导入回退

仅在 B3 不可用时允许。

官方入口：

```text
https://aka.ms/wslubuntu2004
```

下载目录：

```text
D:\WSL\downloads
```

要求：

1. 保存最终解析 URL；
2. 保存下载时间、字节数和 SHA-256；
3. 不使用第三方镜像；
4. 解压到临时目录；
5. 定位 x64 的 `install.tar.gz` 或等效 rootfs；
6. 保存 rootfs SHA-256；
7. 执行：

```powershell
wsl --import `
  AMPlanner-Ubuntu20 `
  "D:\WSL\AMPlanner-Ubuntu20" `
  "<官方 rootfs tar 路径>" `
  --version 2
```

若官方文件结构无法安全判断，停止并返回：

```text
BLOCKED_S1_R1_OFFICIAL_ROOTFS_FORMAT
```

禁止从 `AirFAR-Ubuntu20` 导出克隆。

## 17. B5：初始化专用用户

首先以 root 只读确认：

```powershell
wsl -d AMPlanner-Ubuntu20 -u root -- cat /etc/os-release
wsl -d AMPlanner-Ubuntu20 -u root -- uname -a
wsl --list --verbose
```

必须确认：

```text
VERSION_ID=20.04
WSL version=2
```

然后创建：

```text
用户：amplanner
HOME：/home/amplanner
Shell：/bin/bash
附加组：sudo
```

允许在这个完全隔离的本地研究发行版内配置：

```text
amplanner ALL=(ALL) NOPASSWD:ALL
```

写入：

```text
/etc/sudoers.d/90-amplanner
```

权限必须是 0440，并使用 `visudo -cf` 校验。

写入 `/etc/wsl.conf`：

```ini
[user]
default=amplanner
```

只允许终止新发行版以应用默认用户：

```powershell
wsl --terminate AMPlanner-Ubuntu20
```

不得终止其他发行版，不得使用 `wsl --shutdown`。

重新启动并确认：

```powershell
wsl -d AMPlanner-Ubuntu20 -- whoami
wsl -d AMPlanner-Ubuntu20 -- sh -lc 'echo $HOME'
```

预期：

```text
amplanner
/home/amplanner
```

## 18. B6：新环境基线证据

记录：

```text
/etc/os-release
uname -a
id
df -h
free -h
/etc/wsl.conf
APT 源
当前已安装包清单
```

保存发行版安装位置、VHDX 大小、Windows D 盘剩余空间。

禁止修改默认 WSL 发行版。

---

# 第六部分：阶段 C——ROS Noetic 与构建依赖安装

## 19. C0：ROS EOL 合同

文档中必须明确：

```text
ROS Noetic 已 EOL，不再获得官方功能、安全更新或 bug 修复；
其二进制仍由 packages.ros.org 托管；
本项目仅为固定旧版科研复现使用；
环境必须隔离并冻结实际包版本。
```

不得写成“ROS Noetic 当前受官方支持”。

## 20. C1：基础 APT 工具

在新发行版内，以 `amplanner` 用户执行：

```bash
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl wget gnupg2 lsb-release \
  software-properties-common build-essential cmake ninja-build \
  git git-lfs pkg-config unzip zip jq \
  python3 python3-pip python3-venv python3-dev \
  python3-catkin-tools python3-rosdep python3-vcstool \
  libeigen3-dev libboost-all-dev liboctomap-dev \
  libyaml-cpp-dev pybind11-dev python3-pybind11
```

不得执行 `apt full-upgrade` 或发行版升级。

保存：

```text
apt update 完整日志
安装命令
退出码
下载量
磁盘变化
```

## 21. C2：ROS Noetic 官方源

优先读取既有 `AirFAR-Ubuntu20` 的 ROS 源和 keyring位置作为只读参考，但不得复制其未知文件。

新发行版必须使用官方：

```text
packages.ros.org
raw.githubusercontent.com/ros/rosdistro
```

要求：

1. 使用独立 keyring 文件；
2. 不使用过期的无签名源；
3. 保存 key 文件 SHA-256；
4. 保存 ROS source list；
5. `apt-get update` 成功；
6. 保存 `apt-cache policy`。

安装：

```bash
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ros-noetic-desktop-full \
  ros-noetic-octomap-ros \
  ros-noetic-octomap-server
```

若 `desktop-full` 因个别 EOL 包不可解析，允许回退为：

```bash
ros-noetic-desktop
ros-noetic-ros-base
ros-noetic-rviz
ros-noetic-octomap-ros
ros-noetic-octomap-server
```

但必须记录回退原因和最终包集合。

验证：

```bash
test -f /opt/ros/noetic/setup.bash
rosversion -d
roscore --version || true
dpkg-query -W 'ros-noetic-*'
```

`rosversion -d` 必须输出：

```text
noetic
```

## 22. C3：rosdep

若 `/etc/ros/rosdep/sources.list.d/20-default.list` 不存在：

```bash
sudo rosdep init
```

然后：

```bash
rosdep update --rosdistro noetic
```

若因 Noetic EOL 警告但仍成功，记录为限制；若真正失败，保留日志并允许后续手工依赖安装，但不得伪造成功。

## 23. C4：Miniforge/Conda Python 3.8

禁止污染 Windows Anaconda 和其他 WSL 发行版。

安装路径：

```text
/home/amplanner/miniforge3
```

环境名：

```text
am-planner-py38
```

要求：

1. 从官方 conda-forge/miniforge GitHub release 获取安装器；
2. 记录最终版本、URL、字节数和 SHA-256；
3. 静默安装到用户 HOME；
4. 不修改其他用户配置；
5. 创建 Python 3.8 环境：

```bash
conda create -y -n am-planner-py38 python=3.8 pip
```

6. 安装：

```bash
conda install -y -n am-planner-py38 -c conda-forge autodiff
```

7. 安装基础规划所需的非 IL Python 包。

不得直接执行完整：

```bash
pip install -r requirements.txt
```

因为其中固定了：

```text
torch
torchvision
triton
```

这些属于 IL/学习路径，本轮继续冻结。

可以从 requirements 中安装除上述三项以外、且实际基础脚本需要的包。必须生成：

```text
requirements_basic.txt
requirements_il_frozen.txt
```

其中 `requirements_il_frozen.txt` 至少记录：

```text
torch==2.4.1
torchvision==0.19.1
triton==3.0.0
```

验证：

```bash
conda run -n am-planner-py38 python --version
conda list -n am-planner-py38
```

Python 必须是 3.8.x。

---

# 第七部分：阶段 D——AM-Planner 固定源码与 Catkin 构建

## 24. D0：工作区

使用 Linux ext4 HOME，不得放在 `/mnt/c` 或 `/mnt/d`：

```text
/home/amplanner/am-planner-ws
```

创建：

```bash
mkdir -p /home/amplanner/am-planner-ws/src
mkdir -p /home/amplanner/am-planner-ws/logs
```

## 25. D1：克隆固定源码

```bash
cd /home/amplanner/am-planner-ws/src
git clone https://github.com/SYSU-HILAB/am-planner.git
cd am-planner
git checkout --detach 7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d
```

验证：

```bash
git remote -v
git rev-parse HEAD
git status --short
git submodule status
git lfs ls-files
```

源码必须：

```text
HEAD 完全匹配
工作树干净
无未解释 submodule/LFS
```

禁止使用 Windows 侧 `third_party/am-planner` 的不完整副本。

## 26. D2：源码和环境 manifest

保存：

```text
AM-Planner commit
Git remote
源码树哈希清单
package.xml 清单
APT 包清单
Conda 包清单
ROS 包版本
CMake/GCC/Python 版本
```

## 27. D3：rosdep 依赖解析

在工作区：

```bash
source /opt/ros/noetic/setup.bash
cd /home/amplanner/am-planner-ws

rosdep check --from-paths src --ignore-src --rosdistro noetic
rosdep install --from-paths src --ignore-src --rosdistro noetic -r -y
```

保存所有 unresolved keys。

允许按 README 和源码明确要求补装依赖，但每项必须记录来源。

不得为了缺失包直接复制 `AirFAR-Ubuntu20` 的库文件。

## 28. D4：Catkin 配置

激活环境并扩展 ROS：

```bash
source /home/amplanner/miniforge3/etc/profile.d/conda.sh
conda activate am-planner-py38
source /opt/ros/noetic/setup.bash

cd /home/amplanner/am-planner-ws

catkin config \
  --extend /opt/ros/noetic \
  --cmake-args \
    -DCMAKE_BUILD_TYPE=Release \
    -DPYTHON_EXECUTABLE="$CONDA_PREFIX/bin/python"
```

先执行：

```bash
catkin clean -y
catkin build --summarize --no-status
```

完整日志保存到：

```text
/home/amplanner/am-planner-ws/logs/build_attempt_01.log
```

## 29. D5：有限依赖修复循环

若构建失败，只允许最多 3 轮：

```text
读取首个真实错误
→ 判断缺失系统/ROS/Conda/Python 依赖
→ 安装最小明确依赖
→ 重新构建
```

每轮必须保存：

```text
错误摘要
安装的包
安装前后版本
构建日志
退出码
```

允许安装依赖；禁止修改 AM-Planner 核心源码。

如果错误属于：

```text
源码不兼容
缺少私有文件
严重 API 错误
必须启用 IL/torch/CUDA
```

停止并返回构建阻断，不得静默打补丁。

## 30. D6：构建验收

必须满足：

```text
catkin build exit=0
所有 AM-Planner 包成功
devel/setup.bash 存在
git status --short 为空
固定 commit 未改变
```

运行：

```bash
source devel/setup.bash
rospack find plan_manage
roslaunch plan_manage run_in_sim_grasp.launch --nodes
roslaunch plan_manage run_in_sim_other.launch --args
```

这一步只检查 launch 解析，不计为正式运行。

---

# 第八部分：阶段 E——三项官方 Basic 示例复现

## 31. E0：运行原则

任务：

```text
T1：grasp
T2：other/write
T3：other/lift
```

禁止：

```text
strike 作为本轮必需任务
IL-guided
Polynomial_DiT checkpoint
源码修改
只看 RViz 动画判成功
```

每个任务必须使用独立 ROS master 生命周期或明确清理前一轮进程。

## 32. E1：建立可重复运行器

在项目仓库中创建：

```text
scripts/reproduce/s1_r1_run_am_planner_basic.ps1
scripts/reproduce/s1_r1_run_am_planner_basic.sh
```

PowerShell 负责调用指定 WSL 发行版；Bash 负责：

1. 激活 Conda；
2. source ROS；
3. source Catkin workspace；
4. 创建独立日志目录；
5. 启动 `roscore`；
6. 启动必要 map/desk 节点；
7. 启动指定 launch；
8. 等待轨迹话题；
9. 捕获 ROS 节点、话题和 trajectory 消息；
10. 收集日志；
11. 只终止本轮启动的 PID；
12. 返回明确退出码。

禁止使用：

```bash
killall
pkill -9 -f ros
```

除非 PID 范围被严格限定且记录。

## 33. E2：无 GUI 优先

官方 `setup.sh` 会启动 RViz。正式数值验收优先不启动 RViz：

```text
只启动必要的 map/desk.py
只启动规划 launch
捕获 trajectory topic
```

若 `map/desk.py` 使用图形后端，允许设置：

```bash
MPLBACKEND=Agg
```

不得修改其算法。

如果基础规划确实必须有显示环境，允许使用 WSLg 或 `xvfb-run`，但必须说明原因。

RViz 截图或视频仅为辅助证据，不是通过条件。

## 34. E3：任务 T1——grasp

启动：

```bash
roslaunch plan_manage run_in_sim_grasp.launch
```

建议单任务总超时：

```text
180 秒
```

必须采集：

```text
rosnode list
rostopic list
rostopic type /trajectory
rostopic type /trajectory_arm
rostopic echo -n 1 /trajectory
rostopic echo -n 1 /trajectory_arm
roslaunch stdout/stderr
ROS log 目录
进程退出状态
任务耗时
```

## 35. E4：任务 T2——other/write

不得修改 `tasks.yaml`。

使用 launch 参数：

```bash
roslaunch plan_manage run_in_sim_other.launch task:=write
```

若 launch 参数名称经源码核验不同，使用真实参数并记录。

采集同 T1。

## 36. E5：任务 T3——other/lift

```bash
roslaunch plan_manage run_in_sim_other.launch task:=lift
```

采集同 T1。

## 37. E6：数值成功判据

每个任务不能仅凭“进程未崩溃”通过。

至少满足：

1. launch 文件解析成功；
2. 核心规划节点存在；
3. `/trajectory` 和 `/trajectory_arm` 的实际类型可解析；
4. 至少捕获一条非空轨迹消息，或源码/实际话题名称核验后捕获等价输出；
5. 消息中不得出现 `nan` 或 `inf`；
6. 轨迹分段数/系数/持续时间不是全零空对象；
7. 日志中没有未处理异常、segfault、abort；
8. 任务在超时内产生规划结果；
9. AM-Planner 源码工作树仍干净；
10. 每个任务都保存独立结果摘要。

如果话题名称与预检推断不同，允许根据 `rostopic list` 和源码确定真实名称，但必须保存证据。

## 38. E7：重复性检查

至少选择三项中的一项重复运行 2 次，优先 `grasp`。

比较：

```text
是否两次都成功
规划时间
轨迹消息结构
分段数
总持续时间
关键日志
```

不要求数值逐位相同，但差异必须可解释。

---

# 第九部分：证据、状态和自动检查

## 39. 证据目录

必须至少形成：

```text
docs/evidence/S1-R1/
├─ s1_r0_merge_snapshot.json
├─ wsl_online_list.txt
├─ wsl_install_log.txt
├─ distro_baseline.json
├─ official_image_manifest.json
├─ ros_source_and_key_manifest.md
├─ apt_install_log.txt
├─ ros_package_manifest.txt
├─ conda_installer_manifest.json
├─ conda_package_manifest.txt
├─ requirements_basic.txt
├─ requirements_il_frozen.txt
├─ am_planner_source_manifest.txt
├─ rosdep_check.txt
├─ rosdep_install.txt
├─ build_attempts/
├─ build_summary.txt
├─ grasp/
├─ write/
├─ lift/
├─ repeatability/
├─ structure_check.txt
├─ large_file_scan.txt
├─ secret_scan.txt
└─ git_state.txt
```

原始超大 APT/Catkin/ROS 日志如超过 Git 合理体积，可：

- 压缩后仍小于 10 MB 再提交；或
- 保存在本地 WSL 日志目录；
- 在 Git 中提交摘要、SHA-256、字节数和绝对路径 manifest。

不得提交 WSL VHDX、Appx、rootfs、第三方源码、模型或大视频。

## 40. 进度总控升级

将 v1.3 归档为：

```text
docs/archive/01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.3.md
```

创建：

```text
01_空中机械臂驱鸟器仿真研究项目_进度总控_v1.4.md
```

保留完整协作合同，并更新：

```text
版本：v1.4
S0：PASS_WITH_LIMITATIONS
S1-R0：PASS
当前任务：S1-R1
S1：IN_PROGRESS
S2–S8：FROZEN
允许 IL/checkpoint：否
允许 Isaac Lab：否
允许长训练：否
```

任务执行完成后，只能写：

```text
S1-R1：SUBMITTED_FOR_REVIEW
```

不得自行写 `PASS`。

更新 README 指向 v1.4。

## 41. S1-R1 自动检查

创建：

```text
scripts/audit/check_s1_r1_reproduction.py
```

至少检查：

1. v1.4 存在；
2. v1.3 已归档；
3. S0 为 `PASS_WITH_LIMITATIONS`；
4. S1-R0 为 `PASS`；
5. S1-R1 为 `SUBMITTED_FOR_REVIEW`；
6. S2–S8 为 `FROZEN`；
7. 新发行版名正确；
8. OS 为 Ubuntu 20.04；
9. WSL 为 version 2；
10. ROS distro 为 noetic；
11. ROS 包 manifest 存在；
12. Conda Python 为 3.8；
13. AM-Planner commit 正确；
14. 第三方工作树干净；
15. Catkin build exit=0；
16. 三项任务均有结果摘要；
17. 每项均捕获轨迹证据；
18. 重复性证据存在；
19. IL requirements 已冻结；
20. 没有 checkpoint；
21. 没有大文件；
22. 没有凭据；
23. 报告没有“已完成 S1/S2”的虚假声明。

最终目标：

```text
errors=0
warnings=0
```

如果某个非核心限制需要 warning，必须在最终状态中使用有限状态，不得隐藏。

---

# 第十部分：报告与状态判定

## 42. S1-R1 报告

`docs/reports/S1-R1_install_build_reproduction_report.md` 至少包含：

1. PR #2 merge commit；
2. S1-R1 分支基准；
3. WSL 创建方法；
4. 官方镜像或安装来源和哈希；
5. 新发行版位置、版本、用户；
6. ROS Noetic EOL 声明；
7. ROS 安装包与版本；
8. Conda/Miniforge 版本和哈希；
9. Python 3.8 环境；
10. Basic/IL 依赖分离；
11. AM-Planner commit；
12. rosdep 结果；
13. 三轮以内构建过程；
14. 最终 build 结果；
15. grasp 结果；
16. write 结果；
17. lift 结果；
18. 重复性结果；
19. 轨迹消息和数值检查；
20. 源码是否修改；
21. 明确未下载 checkpoint；
22. 失败和限制；
23. 是否允许高级总控将 S1-R1 判为通过；
24. 下一步只能建议 S1-R2：轨迹导出和官方结果结构化，不得进入 S2。

## 43. 允许的最终状态

### `SUBMITTED_S1_R1_OFFICIAL_BASIC_REPRO`

仅当同时满足：

```text
PR #2 已合并
新发行版创建成功
ROS Noetic 安装成功
Python 3.8/Autodiff 环境成功
AM-Planner 固定 commit 构建成功
grasp 成功并有轨迹证据
write 成功并有轨迹证据
lift 成功并有轨迹证据
至少一项重复成功
源码未修改
未下载 checkpoint
自动检查通过
```

### `SUBMITTED_S1_R1_BUILD_WITH_RUNTIME_BLOCKER`

环境和构建成功，但一个或多个官方任务未产生合格轨迹。必须提供根因证据，不得宣称复现成功。

### `BLOCKED_S1_R1_DISTRO_CREATION`

新 Ubuntu 20.04 发行版无法安全创建。

### `BLOCKED_S1_R1_ROS_INSTALL`

发行版成功，但 ROS Noetic 官方二进制无法安装。

### `BLOCKED_S1_R1_ENVIRONMENT`

ROS 可用，但 Conda/Autodiff 或关键构建环境无法建立。

### `BLOCKED_S1_R1_BUILD`

固定源码无法在不修改核心算法的情况下构建。

### `REVISION_REQUIRED`

实现和证据不完整，无法可信分类。

---

# 第十一部分：GitHub 提交和 Draft PR #3

## 44. 最终检查

运行：

```powershell
python -m compileall scripts
python scripts/audit/check_s0_structure.py
python scripts/audit/check_s1_preflight.py
python scripts/audit/check_s1_r1_reproduction.py
git diff --check
```

检查大文件、凭据和工作树。

## 45. 提交建议

根据实际修改可使用：

```text
chore(s1): provision isolated AM-Planner WSL environment
repro(s1): build and run official basic AM-Planner tasks
docs(s1): record installation and reproduction evidence
```

不得提交第三方源码、环境二进制或 checkpoint。

推送：

```powershell
git push -u origin agent/s1-r1-am-planner-install-basic-repro
```

创建 Draft PR #3：

```text
标题：
[S1-R1] Install and reproduce AM-Planner official basic tasks

Base：
main

Head：
agent/s1-r1-am-planner-install-basic-repro

Draft：
是
```

PR 正文必须包含：

- PR #2 merge commit；
- S1-R1 最终 commit；
- WSL 创建方法；
- ROS/Conda/AM-Planner 版本；
- build 结果；
- 三项任务结果；
- 轨迹证据；
- 重复性；
- 未下载 IL/checkpoint；
- 限制和请求高级总控审查。

不得合并 PR #3。

---

# 第十二部分：最终回报模板

```text
1. 最终执行状态
SUBMITTED_S1_R1_OFFICIAL_BASIC_REPRO
或
SUBMITTED_S1_R1_BUILD_WITH_RUNTIME_BLOCKER
或
BLOCKED_S1_R1_DISTRO_CREATION
或
BLOCKED_S1_R1_ROS_INSTALL
或
BLOCKED_S1_R1_ENVIRONMENT
或
BLOCKED_S1_R1_BUILD
或
REVISION_REQUIRED

2. 阶段 A：S1-R0 收口
开始 Head：
状态提交：
PR #2 Ready：
PR #2 merge commit：
main commit：

3. S1-R1 Git
分支：
基准 main：
新增提交：
最终 commit：
远端 commit：
Draft PR #3：
工作树：

4. WSL 新发行版
创建方式：
发行版名：
Windows 安装位置：
Ubuntu 版本：
WSL 版本：
默认用户：
磁盘占用：
是否改动其他发行版：

5. ROS Noetic
源：
key SHA-256：
安装包集合：
rosversion：
精确包版本清单：
EOL 限制：

6. Python/Conda
安装器：
安装器 SHA-256：
Conda 版本：
环境名：
Python 版本：
autodiff：
Basic requirements：
冻结的 IL requirements：

7. AM-Planner
仓库：
commit：
工作区：
源码工作树：
rosdep：
Catkin build：
构建轮次：
是否修改源码：

8. grasp
启动命令：
退出/超时：
节点：
轨迹话题：
轨迹消息：
数值检查：
规划耗时：
结论：

9. other/write
<同上>

10. other/lift
<同上>

11. 重复性
重复任务：
两次结果：
差异：

12. 自动检查
compileall：
S0 regression：
S1-R0 regression：
S1-R1 check：
errors：
warnings：
git diff --check：
大文件：
凭据扫描：

13. 明确未执行
未修改 AirFAR：
未修改其他 WSL：
未下载 Polynomial_DiT checkpoint：
未运行 IL：
未安装 Isaac Lab：
未训练：
未进入 S2：
未合并 PR #3：

14. 关键证据路径

15. 风险与限制

16. 下一阶段建议
只判断是否允许设计 S1-R2 轨迹导出、结构化校验和官方任务结果固化，不得自行开始。
```

任何成功声明必须由 Git commit、命令退出码、ROS 话题、轨迹消息和原始日志共同支撑。
