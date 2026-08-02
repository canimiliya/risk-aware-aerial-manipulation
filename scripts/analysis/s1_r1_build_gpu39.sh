#!/usr/bin/env bash
set -o pipefail
source /home/amplanner/miniforge3/etc/profile.d/conda.sh
conda activate am-planner-gpu-probe-py39
export ROS_DISTRO=noetic
set +u
source /opt/ros/noetic/setup.bash
if [ -f /home/amplanner/am-planner-gpu39-ws/devel/setup.bash ]; then
  source /home/amplanner/am-planner-gpu39-ws/devel/setup.bash
fi
set -u
GPU39_WS=/home/amplanner/am-planner-gpu39-ws
TAG=${S1_R1_BUILD_TAG:-01}
cd "$GPU39_WS"
/usr/bin/catkin build --summarize --no-status --verbose 2>&1 | tee "$GPU39_WS/logs/abi_build_attempt_${TAG}.log"
rc=${PIPESTATUS[0]}
printf '%s\\n' "$rc" > "$GPU39_WS/logs/abi_build_attempt_${TAG}.exit_code"
exit "$rc"
