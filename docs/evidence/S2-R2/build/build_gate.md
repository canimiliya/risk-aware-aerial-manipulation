# S2-R2 build gate

Decision: build gate passed in the required clean S2-R2 workspace.

- Workspace: `/home/amplanner/am-planner-s2-r2-ws`.
- Official source commit: `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`.
- Accepted ABI patch: only `src/plan/plan_manage/CMakeLists.txt` and `src/plan/traj_opt/CMakeLists.txt`; canonical LF SHA-256 `8bd9fa32c508495bd1f98f77b529205323ecbdf59c9031be2ec75790c33f7db6`.
- Catkin result: 19 project packages succeeded, 0 failed, 0 abandoned. Upstream warning-bearing packages are retained in the raw build log and are not relabeled as zero warnings.
- Runtime artifacts: `devel/.private/plan_manage/lib/plan_manage/se3_node` and `devel/.private/traj_opt/lib/libse3_planner.so`.
