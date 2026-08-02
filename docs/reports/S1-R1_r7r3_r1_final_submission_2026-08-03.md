# R7-R3-R1 最终提交报告

## 结论

本轮已完成 S1-R1 任务卡授权范围内的工作。三项告警均已引用原始证据并接受为限制；最终接受审计为 `errors=[]`、`unresolved_warnings=[]`。这不是零告警 PASS，也不代表整个 S1 PASS。

## 当前做到的

- `.coordination` 处理：保留 19 个文件、73,881 bytes；未跟踪、未删除、未提交；仅在 `.git/info/exclude` 加入 `/.coordination/`。
- ROS overlay：隔离路径 `/home/amplanner/ros-noetic-py39-overlay-r7r3-r1`，官方 Noetic 冻结 commit 已记录。
- AM-Planner 补丁：固定 base commit `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`；仅修改两个 CMakeLists；patch SHA256=`8bd9fa32c508495bd1f98f77b529205323ecbdf59c9031be2ec75790c33f7db6`。
- 构建：发现 19 个项目包，0 failed、0 abandoned；Catkin 汇总因 prebuild 显示 20 succeeded，另有 8 个 warning-bearing packages。
- 完整 ABI：`libse3_planner.so`、`se3_node`、overlay ROS libraries 均为 Python 3.9；完整 Python 3.8 occurrence=0；runtime not-found=0。
- 解释器/GPU：Python 3.9.23、Torch 2.7.1+cu128、CUDA=True、RTX 5060 Ti、capability=(12,0)；normal 与 env-i 探针通过。
- write：成功运行 `write_r7r3_r1_gpu_run_02`，19 段双轨迹，390 个数值字段，NaN/Inf=0；JPS、MINCO、CUDA 日志齐全。
- grasp：`grasp_r7r3_r1_gpu_run_02` 成功，4 段双轨迹，NaN/Inf=0。
- lift：`lift_r7r3_r1_gpu_run_01` 成功，3 段双轨迹，NaN/Inf=0。
- 重复性：`grasp_r7r3_r1_gpu_run_03` 成功；与第一次 grasp 结构、持续时间一致，规划耗时和 GPU 峰值显存已比较。
- 告警审查：三项告警分别分类为 `NON_BLOCKING_UPSTREAM`、`NON_BLOCKING_ENVIRONMENT`、`NON_BLOCKING_POST_SUCCESS`；原始文本未删除。
- 最终接受：`docs/evidence/S1-R1/final_acceptance/s1_r1_final_acceptance.json`，`errors=[]`、`unresolved_warnings=[]`。
- GitHub：运行证据提交 `b0616730685b250e0804ec4721dde23383b6d87a` 已推送；最终审计与格式报告提交为 `3f09402740ed4b7e62b5ea8779b767ce8f519eac`；PR #3 当前仍为 Open + Draft + CLEAN，未合并。

## 还缺什么

S1-R1 已按授权规则收口为 `PASS_WITH_LIMITATIONS`。仍缺的是 S1-R2 的结构化轨迹合同、waypoint 变体、可视化和其独立 Draft PR；三项告警限制仍需负责人知悉。

## 是否算通过

S1-R1 算通过，但只算 `PASS_WITH_LIMITATIONS`；整个 S1 不算通过，仍为 `IN_PROGRESS`。

## 是否需要项目负责人处理

需要负责人知悉并接受上述三项限制；S1-R2 仍是独立审阅门槛，S2–S8 继续冻结。

## 原始标签

`PASS_WITH_LIMITATIONS`：人话是“官方 Python 3.9 ABI 和 GPU 基础轨迹链已经真实跑通，三项告警有原始证据且暂不阻断本轮，但不是零告警通过，也不是整个 S1 通过”。

## Git

- 开始 Head：`5b12ec829b826392675ab732c53cda96b7550ad7`
- 运行证据提交：`b0616730685b250e0804ec4721dde23383b6d87a`
- 最终审计与格式报告提交：`3f09402740ed4b7e62b5ea8779b767ce8f519eac`
- PR #3：Open + Draft + CLEAN
- 工作树：干净
- stash：`stash@{0}`、`stash@{1}` 均保留

## `.coordination`

- 是否已跟踪：否
- 文件数/总大小：19 / 73,881 bytes
- 清单 SHA：见 `coordination_inventory.json`
- 是否删除：否
- 是否提交：否
- `.git/info/exclude`：仅新增本地 `/.coordination/` 规则

## ROS overlay

- 源码仓库/commit：官方 `ros/rospack` `fd4d6fd87895c389c58b52e4009fe0b793769818`；官方 `ros/ros` `99fd9bb76338f3315cd0a89af700d789ef337ea6`
- 系统包版本：见 `r7r3_r1_ros_overlay/system_package_versions.txt`
- 构建包：rospack、roslib；3 次尝试记录完整
- librospack Python NEEDED：仅 Python 3.9
- libroslib 闭包：Python 3.9，无 Python 3.8、无 not-found
- rospack/getPath 探针：返回新 overlay 的 roslib 路径

## AM-Planner

- base commit：`7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`
- 修改文件：`src/plan/traj_opt/CMakeLists.txt`、`src/plan/plan_manage/CMakeLists.txt`
- patch SHA：`8bd9fa32c508495bd1f98f77b529205323ecbdf59c9031be2ec75790c33f7db6`
- ROS 库集合：保留 Catkin ROS libraries，局部过滤 Python 3.8 并显式加入 Python3::Python/pybind11::embed
- 19/19：19 个项目包成功，0 failed、0 abandoned

## ABI

- libse3_planner：直接 Python 3.9；无 Python 3.8
- se3_node：直接 Python 3.9；无 Python 3.8
- 完整闭包：Python 3.8 occurrence=0；runtime not-found=0
- link.txt：Python 3.8 occurrence=0
- CMakeCache：有效 Python 路径均指向 GPU Conda Python 3.9
- not found：0

## 解释器/GPU

- Python：3.9.23
- sys.path：仅 Python 3.9 路径，无 python3.8、无 python38.zip
- filesystem encoding：utf-8
- Torch：2.7.1+cu128
- CUDA：True
- GPU：NVIDIA GeForce RTX 5060 Ti，capability=(12,0)

## write

- 实际耗时：监视样本最后 elapsed 438.018 s；捕获成功
- GPU 使用：roslaunch 明确 `Using device: cuda`；GPU 利用率 10–13%，显存峰值 2386 MB；nvidia-smi 进程名为 `[Not Found]`
- JPS：JPS search path 成功，搜索耗时 1.547 s
- MINCO：setup successfully，Finish optimization
- `/trajectory`：19 段、390 数值字段、非空
- `/trajectory_arm`：19 段、390 数值字段、非空
- NaN/Inf：两条均 0/0
- 非零数据/持续时间：379/232 与 377/192；19 个正持续时间，总时长 10.4005 s
- 结果：成功；第一次运行器失败和第二次成功均保留

## grasp/lift/重复性

grasp、lift、重复 grasp 均在 300 秒内成功捕获双轨迹，capture_exit=0，NaN/Inf=0；两次 grasp 均 4 段、总持续时间 5.88045 s，规划耗时 3572.68 ms 与 3374.95 ms，GPU 峰值显存 1921 MB 与 1860 MB。

## 基线保护

- CPU 工作区：未通过本轮命令修改；历史 before/after baseline 保留
- 旧 GPU 工作区：未操作；既有旧 runner 进程保持原状
- 旧 GPU39 工作区：未操作
- CPU 环境：未升级或替换
- GPU 环境：未升级或替换；仅使用既有 GPU probe 环境
- `/opt/ros/noetic`：未覆盖
- stash：未操作，两个 stash 仍在

## 自动检查

- errors：专用审计 0
- warnings：3 条真实告警；不伪造为 0
- git diff --check：通过
- 大文件：0 个超过 10 MB
- 凭据：未发现凭据模式

## 明确未执行

- 未删除 `.coordination`
- 未修改算法
- 未修改任务参数
- 未覆盖系统 ROS
- 未运行 IL/Polynomial_DiT
- 未进入 S2
- 未合并 PR #3

## 关键证据路径

- `docs/evidence/S1-R1/r7r3_r1_state_gate/`
- `docs/evidence/S1-R1/r7r3_r1_ros_overlay/`
- `docs/evidence/S1-R1/r7r3_r1_integration/`
- `docs/evidence/S1-R1/r7r3_r1_runtime/`
- `docs/evidence/S1-R1/r7r3_r1_state_gate/r7r3_r1_audit.json`
