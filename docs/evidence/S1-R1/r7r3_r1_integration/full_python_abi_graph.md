# 完整 Python ABI 图

结论：通过。当前运行时 `LD_LIBRARY_PATH` 下，`libse3_planner.so`、`se3_node`、ROS Python 3.9 overlay 的 `librospack.so` 和 `libroslib.so` 均无 `not found`；闭包中没有 `libpython3.8`，只解析到 Python 3.9。

| 对象 | 直接 Python NEEDED | Python 3.8 | 运行时 not found | SHA-256 |
|---|---|---:|---:|---|
| `libse3_planner.so` | `libpython3.9.so.1.0` | 0 | 0 | `e6210edcc376bf3044c95fee16c30da7b86acfe0ba717a35d17457d7eb1ad4bf` |
| `se3_node` | `libpython3.9.so.1.0` | 0 | 0 | `bb4bdc17112efa565b9825f0efa9b76e86525687fb20b7b2961acae21e881a4c` |
| overlay `librospack.so` | `libpython3.9.so.1.0` | 0 | 0 | `bc23660095892f5f05ed759bcbcca6dfe31ef3a6301333e70d6027e10579af34` |
| overlay `libroslib.so` | 直接无 Python；传递为 `libpython3.9.so.1.0` | 0 | 0 | `e644a3f8183709a44d4718e499f29356442b187be8a03690b4b350c5fe4a73ca` |

`traj_opt` 和 `plan_manage` 的 `link.txt` 均无 Python 3.8；CMakeCache 的 Python 解释器、头文件和库均指向 `am-planner-gpu-probe-py39`。首次未带运行时库路径的 `ldd` 原始诊断也保留在 `full_abi_raw.log`，最终结论以带实际运行时路径的 `ldd_runtime.log` 为准。
