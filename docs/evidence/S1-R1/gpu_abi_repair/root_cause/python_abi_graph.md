# Python ABI graph

- classification: `BOTH_DIRECT_AND_TRANSITIVE`
- direct NEEDED: read from each ELF's `readelf -d` output
- transitive/runtime resolution: read from each ELF's `ldd` output

## se3_node
- path: `/home/amplanner/am-planner-gpu-ws/devel/.private/plan_manage/lib/plan_manage/se3_node`
- direct NEEDED: libse3_planner.so, libroslib.so, libpython3.8.so.1.0, libroscpp.so, librosconsole.so, libxmlrpcpp.so, libroscpp_serialization.so, librostime.so, libpython3.9.so.1.0, libstdc++.so.6, libgcc_s.so.1, libc.so.6
- ldd Python lines: 	libpython3.8.so.1.0 => /lib/x86_64-linux-gnu/libpython3.8.so.1.0 (0x000070428bc00000) | 	libpython3.9.so.1.0 => /home/amplanner/miniforge3/envs/am-planner-gpu-probe-py39/lib/libpython3.9.so.1.0 (0x000070428b600000)

## libse3_planner.so
- path: `/home/amplanner/am-planner-gpu-ws/devel/.private/traj_opt/lib/libse3_planner.so`
- direct NEEDED: libpcl_common.so.1.10, libjps3d.so, libroslib.so, libpython3.8.so.1.0, libroscpp.so, librosconsole.so, libroscpp_serialization.so, librostime.so, libstdc++.so.6, libm.so.6, libgcc_s.so.1, libc.so.6, ld-linux-x86-64.so.2
- ldd Python lines: 	libpython3.8.so.1.0 => /lib/x86_64-linux-gnu/libpython3.8.so.1.0 (0x00007e953d200000)

## libroslib.so
- path: `/opt/ros/noetic/lib/libroslib.so`
- direct NEEDED: librospack.so, libpthread.so.0, libstdc++.so.6, libgcc_s.so.1, libc.so.6
- ldd Python lines: 
