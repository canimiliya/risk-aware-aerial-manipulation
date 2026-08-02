# R7-R3-R1 baseline protection

- CPU source/environment baseline evidence remains the existing before/after pair under `docs/evidence/S1-R1/gpu_rebuild/cpu_baseline_before/` and `cpu_baseline_after/`; common tracked source and environment manifests are unchanged.
- This run used only the new isolated WSL paths `/home/amplanner/ros-noetic-py39-overlay-r7r3-r1` and `/home/amplanner/am-planner-r7r3-r1-ws`.
- The pre-existing CPU workspace, old GPU workspace, old GPU39 workspace, `/opt/ros/noetic`, and both stashes were not modified by this task. The pre-existing old runner process was observed and left untouched.
- No `patchelf`, `LD_PRELOAD`, global `killall`/`pkill`, force push, rebase, reset, clean, system ROS replacement, CUDA Toolkit installation, or S2 action was executed.
- `.coordination/S1-R1-R7-R2/` remains present with 19 files and 73,881 bytes; it is not tracked or submitted.
