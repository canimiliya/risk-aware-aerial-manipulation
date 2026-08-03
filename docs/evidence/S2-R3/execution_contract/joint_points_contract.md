# S2-R3 getJointPoints 合同

`delta_display.cpp:632-713` 的 `getJointPoints` 只读输出：

- `A[3]`：固定平台三个主动臂根点；
- `B[3]`：三个主动上臂末端；
- `C[3]`：移动平台三连接点；
- `B_left/B_right[3]` 与 `C_left/C_right[3]`：六条下部平行杆的两端。

项目 wrapper 按同样的 `phi=[π/6,5π/6,3π/2]`、`R/r/L/l` 和旋转构造生成点，所有下游碰撞结果标记为 `DERIVED_FROM_OFFICIAL` 的中心线 capsule，而非 mesh 精确碰撞。
