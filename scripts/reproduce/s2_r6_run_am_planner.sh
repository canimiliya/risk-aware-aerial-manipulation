#!/usr/bin/env bash
set -euo pipefail

variant="${1:?usage: s2_r6_run_am_planner.sh nominal run-id timeout-s [envelope-config]}"
run_id="${2:?run id required}"
timeout_s="${3:?timeout seconds required}"
config_file="${4:-/mnt/d/Desktop/my_project/Simulation_Research_on_Aerial_Manipulator_for_Power_Line_Bird_Diverter_Operation/docs/evidence/S2-R6/configs/s2_r6_disabled.yaml}"
case "$variant" in smoke_free|loose|nominal|narrow) ;; *) exit 64 ;; esac

workspace=/home/amplanner/am-planner-s2-r6-ws
overlay=/home/amplanner/ros-noetic-py39-overlay-r7r3-r1
conda_root=/home/amplanner/miniforge3/envs/am-planner-gpu-probe-py39
repo=/mnt/d/Desktop/my_project/Simulation_Research_on_Aerial_Manipulator_for_Power_Line_Bird_Diverter_Operation
run_dir="$repo/docs/evidence/S2-R6/runtime/$run_id"
capture_script="$repo/scripts/reproduce/s1_r1_capture_ros_message.py"
map_script="$repo/planner_bridge/scenes/publish_s2_r2_crossarm_map.py"
launch_file="$repo/planner_bridge/scenes/s2_r6_official.launch"

mkdir -p "$run_dir"
exec >"$run_dir/runner.log" 2>&1
source /home/amplanner/miniforge3/etc/profile.d/conda.sh
conda activate am-planner-gpu-probe-py39
export ROS_DISTRO=noetic ROS_VERSION=1 ROS_MASTER_URI=http://localhost:11311
source /opt/ros/noetic/setup.bash
source "$overlay/devel/setup.bash"
source "$workspace/devel/setup.bash"
export PATH="$conda_root/bin:/opt/ros/noetic/bin:/usr/bin:/bin:/usr/lib/wsl/lib"
export ROS_PACKAGE_PATH="$workspace/src:$overlay/src:/opt/ros/noetic/share"
export ROS_HOME="$run_dir/ros_home"
export LD_LIBRARY_PATH="$workspace/devel/lib:$overlay/devel/lib:$conda_root/lib:$conda_root/lib/python3.9/site-packages/torch/lib:/opt/ros/noetic/lib:/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu"
export PYTHONPATH="$workspace/devel/lib/python3/dist-packages:$overlay/devel/lib/python3/dist-packages:/opt/ros/noetic/lib/python3/dist-packages:/usr/lib/python3/dist-packages"
mkdir -p "$ROS_HOME"
runtime_bin="$run_dir/runtime-bin"
mkdir -p "$runtime_bin"
tr -d '\r' < "$repo/scripts/reproduce/s2_r2_rosversion_wrapper.sh" > "$runtime_bin/rosversion"
chmod +x "$runtime_bin/rosversion"
export PATH="$runtime_bin:$PATH"

{
  printf 'stage=S2-R6\nvariant=%s\nrun_id=%s\ntimeout_s=%s\nworkspace=%s\nconfig=%s\n' "$variant" "$run_id" "$timeout_s" "$workspace" "$config_file"
  env | sort
  printf 'source_head='; git -C "$workspace/src/am-planner" rev-parse HEAD
  sha256sum "$workspace/src/am-planner/src/plan/traj_opt/CMakeLists.txt" "$workspace/src/am-planner/src/plan/plan_manage/CMakeLists.txt"
} >"$run_dir/command.txt"
env | sort >"$run_dir/environment.txt"

env PYTHONPATH="$PYTHONPATH" /opt/ros/noetic/bin/roscore >"$run_dir/roscore.log" 2>&1 & roscore_pid=$!
env PYTHONPATH="$PYTHONPATH" /usr/bin/python3 "$map_script" --variant "$variant" >"$run_dir/map.log" 2>&1 & map_pid=$!
for _ in $(seq 1 60); do
  if env PYTHONPATH="$PYTHONPATH" /opt/ros/noetic/bin/rosparam list >/dev/null 2>&1; then break; fi
  sleep 1
done
env PYTHONPATH="$PYTHONPATH" /opt/ros/noetic/bin/rosparam list >/dev/null
env PYTHONPATH="$PYTHONPATH" /usr/bin/python3 "$capture_script" --output-dir "$run_dir" --timeout-s "$timeout_s" >"$run_dir/capture.log" 2>&1 & capture_pid=$!
sleep 2
env PYTHONHOME="$conda_root" PYTHONPATH="$conda_root/lib/python3.9/site-packages:$PYTHONPATH" "$conda_root/bin/python" /opt/ros/noetic/bin/roslaunch --screen "$launch_file" task:="$variant" envelope_config:="$config_file" >"$run_dir/roslaunch.log" 2>&1 & launch_pid=$!
set +e
wait "$capture_pid"; capture_status=$?
kill "$launch_pid" "$map_pid" "$roscore_pid" 2>/dev/null
wait "$launch_pid" "$map_pid" "$roscore_pid" 2>/dev/null
set -e
printf '{"variant":"%s","run_id":"%s","capture_exit":%s,"launch_pid":%s,"map_pid":%s,"roscore_pid":%s}\n' "$variant" "$run_id" "$capture_status" "$launch_pid" "$map_pid" "$roscore_pid" >"$run_dir/processes.json"
exit "$capture_status"
