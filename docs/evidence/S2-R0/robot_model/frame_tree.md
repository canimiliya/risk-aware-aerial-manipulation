# S2-R0 坐标树

```text
W (world, dynamic)
└── B (official URDF link: body)
    └── A0 (official URDF link: end_effector / arm-base platform)
        └── E (FK moving-platform center; semantic alias for the planning contract)
            └── T (tool axis; provisional task axis, not present in the ROS message)
```

- `B→A0`：来自 `arm.xacro` 的 fixed joint `ini_connect`，平移 `[0, 0, -0.05] m`、RPY `[0, 0, -1.5708] rad`，静态，官方。
- `A0→E`：由 `delta_display.cpp::FK_kin` 的闭链 FK 计算，单位 m，动态，官方几何公式。
- `E→T`：本轮只定义候选作业的水平工具轴 `[1,0,0]`；没有官方工具姿态字段，标记 `PROVISIONAL_S2_ASSUMPTION`。
- `W→B`：飞行器位姿由完整规划/仿真决定，本轮不执行，不用假设值冒充已验证动态变换。
