# S2-R4 official asset search

审计对象是固定官方 AM-Planner/DeltaDisplay 执行链；本文件只记录检索结果，不替换官方资产。

| 项目 | 官方来源/结果 | S2-R4 处理 |
|---|---|---|
| arm URDF/Xacro | AM-Planner-Ubuntu20 工作区的 `arm.xacro`，使用 `drone.dae`；未发现可直接用于 `DeltaDisplay::getJointPoints` 的 body/rotor 半径合同 | 保留现有代理合同 |
| base/rotor mesh | 官方运行链可加载 mesh，但未公开与执行层 proxy 一一对应的 rotor disk center/radius 元数据 | 不从 mesh 反推新尺寸 |
| Delta joint geometry | 官方 `DeltaDisplay` 的 `IK_kin`/`FK_kin`/`getJointPoints` 已在项目内逐式复核 | 使用现有官方公式 |
| obstacle geometry | S2-R2/S2-R3 固定横担场景与既有障碍点集 | 不移动、不缩小、不删除 |

已记录的只读资产哈希：`arm.xacro` = `8489da676645edebde53e0ac352a48bc1a3096f5ee41bb86122afdaca5ca6db1`；官方运行 launch = `dce851f5d24b6d153f4ee7df147309b46212aa646dd9c180485b1eb92972dfb7`。固定 AM-Planner commit 为 `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`。

结论：当前仍没有足够官方元数据替代 S2 代理；`body=0.20 m`、`rotor disk radius=0.25 m`、现有 rotor centers、官方 joint-point 中心线加既有 capsule、platform/EE `0.025 m` 继续作为 provisional contract，并在本轮重新验收，不得把它称为 mesh 精确碰撞。
