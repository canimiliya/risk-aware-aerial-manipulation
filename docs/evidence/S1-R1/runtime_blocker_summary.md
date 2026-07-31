# S1-R1 runtime blocker evidence

- Build gate: `/usr/bin/catkin build --summarize --no-status` completed with `All 19 packages succeeded` and exit 0.
- Fixed upstream source: `7ea9a0a4c5a338efee1bf97c7f7e3e638e7d0d5d`; source status was clean before runtime attempts.
- The final grasp attempt launched `se3_node`, received the point cloud, completed both JPS searches, and entered MINCO optimization.
- It then terminated with `ModuleNotFoundError: No module named 'torch'` and `[Workspace_Model_H]: Failed to initialize workspace probability model`.
- The detailed evidence is `runtime/s1-r1-runtime/grasp_run_01_retry_03/roslaunch.log`; both trajectory topics were present but neither produced a message before the node aborted.
- No torch, torchvision, triton, checkpoint download, IL script, third-party source edit, PR merge, or S2 work was performed.
- The correct result is a runtime blocker, not a successful basic trajectory reproduction.
