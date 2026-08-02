#!/usr/bin/env bash
set -e
exec env -u PYTHONHOME \
  PYTHONPATH=/home/amplanner/am-planner-r7r3-r1-ws/devel/lib/python3/dist-packages:/home/amplanner/ros-noetic-py39-overlay-r7r3-r1/devel/lib/python3/dist-packages:/opt/ros/noetic/lib/python3/dist-packages:/usr/lib/python3/dist-packages \
  /usr/bin/rosversion "$@"
