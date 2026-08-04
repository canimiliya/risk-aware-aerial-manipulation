# S3-R0 trajectory protocol and Isaac Lab environment report

## Outcome

S2 baseline 门槛按本轮权威任务卡纠正后通过；S3-R0 离线轨迹协议已完成并通过纯 Python 测试。平台硬门槛通过但带 warnings。Isaac Lab/Isaac Sim 安装未完成：固定 pip-only 路线在依赖 `flatdict` 构建元数据阶段超时，因此本轮提交为 `SUBMITTED_S3_R0_PROTOCOL_READY_PLATFORM_BLOCKED`，不宣称 Isaac readiness。

## Protocol

输入只使用 S2-R6 `nominal_100w0` 和 `nominal_repeat_final_100w0`。每套输出保存原始 base/arm polynomial、200 Hz canonical full-state、phase annotations、scene contract 和 SHA-256 manifest。q/qdot/qddot 由仓库内 official Delta IK 和 canonical time grid 确定性重建；未从仅有 yaw endpoint 的 Cartesian source 虚构完整末端 quaternion。

## Environment

`D:\i3\s3_isaaclab_232` 的 Python 3.11 环境创建成功。请求版本为 IsaacLab 2.3.2.post1、Isaac Sim 5.1.0、Torch 2.7.0、torchvision 0.22.0/cu128。EULA 未到达/未接受，`isaaclab` 与 `isaacsim` 导入和 PhysX empty-stage smoke 未执行。

## Scope boundary

没有提交安装目录或缓存，没有修改注册表/驱动，没有建立 ROS/ROS2 bridge，没有训练、闭环、风、接触随机化或 S4 工作。
