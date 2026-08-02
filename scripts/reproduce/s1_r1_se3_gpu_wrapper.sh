#!/usr/bin/env bash
# Runtime-only wrapper: keep ROS Python tools separate while se3_node embeds GPU Python 3.9.
set -e
export PYTHONHOME=/home/amplanner/miniforge3/envs/am-planner-gpu-probe-py39
export PYTHONPATH=/home/amplanner/miniforge3/envs/am-planner-gpu-probe-py39/lib/python3.9/site-packages:/home/amplanner/am-planner-gpu-ws/devel/lib/python3/dist-packages:/opt/ros/noetic/lib/python3/dist-packages:/usr/lib/python3/dist-packages
export LD_LIBRARY_PATH=/home/amplanner/miniforge3/envs/am-planner-gpu-probe-py39/lib:/home/amplanner/miniforge3/envs/am-planner-gpu-probe-py39/lib/python3.9/site-packages/torch/lib:/opt/ros/noetic/lib:${LD_LIBRARY_PATH:-}
if [[ -n "${SE3_WRAPPER_LOG:-}" ]]; then env | sort > "$SE3_WRAPPER_LOG"; fi
exec env -i \
  PATH=/home/amplanner/miniforge3/envs/am-planner-gpu-probe-py39/bin:/usr/bin:/bin \
  HOME=/home/amplanner \
  ROS_MASTER_URI="${ROS_MASTER_URI:-http://localhost:11311}" \
  ROS_HOME="${ROS_HOME:-/home/amplanner/.ros}" \
  ROS_LOG_FILENAME="${ROS_LOG_FILENAME:-}" \
  ROS_NAMESPACE="${ROS_NAMESPACE:-}" \
  ROS_PACKAGE_PATH=/home/amplanner/am-planner-gpu-ws/src/am-planner/src:/opt/ros/noetic/share \
  ROS_DISTRO="${ROS_DISTRO:-noetic}" \
  ROS_ROOT="${ROS_ROOT:-/opt/ros/noetic/share/ros}" \
  ROS_ETC_DIR="${ROS_ETC_DIR:-/opt/ros/noetic/etc/ros}" \
  ROS_VERSION="${ROS_VERSION:-1}" \
  PYTHONHOME="$PYTHONHOME" \
  PYTHONPATH="$PYTHONPATH" \
  LD_LIBRARY_PATH="$LD_LIBRARY_PATH" \
  /home/amplanner/am-planner-gpu-ws/devel/.private/plan_manage/lib/plan_manage/se3_node.gpu_real "$@"
