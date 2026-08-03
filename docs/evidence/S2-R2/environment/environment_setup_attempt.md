# S2-R2 environment setup and provenance

- Distro: `AMPlanner-Ubuntu20`, Ubuntu 20.04.3, running.
- Required workspace: `/home/amplanner/am-planner-s2-r2-ws`.
- Source: `/home/amplanner/am-planner-ws/src/am-planner`, with official remote restored to `https://github.com/SYSU-HILAB/am-planner.git`.
- Source HEAD: `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`.
- Source tracked SHA manifest: `0518ef370e84a7d6a7fad4924f080616ea2753170c2a0ce380d8664d1492d528`.
- Alternate GPU39 clone was not selected: `/home/amplanner/am-planner-gpu39-ws/src/am-planner`, HEAD `330db6ccd463a64c2c539bf1a76007895c432683`, tracked SHA `99c1e016460505f6d2fbb20a3764b3000724de038dbf7d17f3bd211859102854`.
- New clone provenance: `/home/amplanner/am-planner-s2-r2-ws/src/am-planner` was clean at the official commit before the accepted ABI patch; after the patch only `src/plan/plan_manage/CMakeLists.txt` and `src/plan/traj_opt/CMakeLists.txt` are modified.
- No build/devel/install directories were copied from another workspace.
- The only source changes are the accepted S1 ABI patch applied to the two package CMakeLists; algorithm source, URDF, system ROS, and Conda packages were not changed.

The old connection-failure notes remain in the preserved historical runtime/setup evidence. The clean S2-R2 workspace was subsequently established from the verified local clone and is the only workspace used for the new build and runtime evidence.
