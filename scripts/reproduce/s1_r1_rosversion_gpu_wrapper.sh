#!/usr/bin/env bash
# Keep roslaunch's command parameter on the system ROS Python, not GPU Python.
set -e
exec env -u PYTHONHOME PYTHONPATH=/home/amplanner/am-planner-gpu-ws/devel/lib/python3/dist-packages:/opt/ros/noetic/lib/python3/dist-packages:/usr/lib/python3/dist-packages /usr/bin/rosversion "$@"
