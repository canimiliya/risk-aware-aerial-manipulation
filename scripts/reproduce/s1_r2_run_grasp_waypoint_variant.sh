#!/usr/bin/env bash
set -euo pipefail

run_id=grasp_waypoint_variant_01
timeout_s=300
workspace=/home/amplanner/am-planner-r7r3-r1-ws
overlay=/home/amplanner/ros-noetic-py39-overlay-r7r3-r1
conda_root=/home/amplanner/miniforge3/envs/am-planner-gpu-probe-py39
repo_mnt=/mnt/d/Desktop/my_project/Simulation_Research_on_Aerial_Manipulator_for_Power_Line_Bird_Diverter_Operation
run_dir="$repo_mnt/docs/evidence/S1-R2/waypoint_variant/$run_id"
capture_script="$repo_mnt/scripts/reproduce/s1_r1_capture_ros_message.py"
monitor_script="$repo_mnt/scripts/reproduce/s1_r1_monitor_gpu_planner.py"
launch_file="$repo_mnt/planner_bridge/variants/grasp_waypoint_variant_01.launch"

mkdir -p "$run_dir"
exec >"$run_dir/runner.log" 2>&1
exec 9>/tmp/s1-r2-waypoint.lock
flock -n 9
source /home/amplanner/miniforge3/etc/profile.d/conda.sh
conda activate am-planner-gpu-probe-py39
export ROS_DISTRO=noetic ROS_VERSION=1 ROS_MASTER_URI=http://localhost:11311
source /opt/ros/noetic/setup.bash
source "$overlay/devel/setup.bash"
source "$workspace/devel/setup.bash"
runtime_bin="$run_dir/runtime-bin"
mkdir -p "$runtime_bin"
ln -sf "$repo_mnt/planner_bridge/variants/rosversion_wrapper.sh" "$runtime_bin/rosversion"
export PATH="$runtime_bin:$conda_root:/opt/ros/noetic/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/lib/wsl/lib"
ros_pythonpath="$workspace/devel/lib/python3/dist-packages:$overlay/devel/lib/python3/dist-packages:/opt/ros/noetic/lib/python3/dist-packages:/usr/lib/python3/dist-packages"
gpu_pythonpath="$conda_root/lib/python3.9/site-packages:$ros_pythonpath"
export LD_LIBRARY_PATH="$workspace/devel/lib:$overlay/devel/lib:$conda_root/lib:$conda_root/lib/python3.9/site-packages/torch/lib:/opt/ros/noetic/lib:/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu"
export ROS_HOME="$run_dir/ros_home" MPLBACKEND=Agg ROS_PACKAGE_PATH="$workspace/src:$overlay/src:/opt/ros/noetic/share"
mkdir -p "$ROS_HOME"
env | sort >"$run_dir/environment.txt"
printf 'task=grasp\nrun_id=%s\ntimeout_s=%s\nlaunch_file=%s\nvariant_object_px=0.05\nbaseline_object_px=0.00\n' "$run_id" "$timeout_s" "$launch_file" >"$run_dir/command.txt"

env PYTHONPATH="$ros_pythonpath" /opt/ros/noetic/bin/roscore >"$run_dir/roscore.log" 2>&1 &
roscore_pid=$!
launch_pid=''
map_pid=''
capture_pid=''
monitor_pid=''
cleanup() {
  set +e
  for pid in "$launch_pid" "$map_pid" "$capture_pid" "$monitor_pid" "$roscore_pid"; do
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null && kill "$pid" 2>/dev/null
  done
  wait "$launch_pid" 2>/dev/null; launch_exit=$?
  wait "$map_pid" 2>/dev/null; map_exit=$?
  wait "$capture_pid" 2>/dev/null; capture_exit=$?
  wait "$monitor_pid" 2>/dev/null; monitor_exit=$?
  wait "$roscore_pid" 2>/dev/null; roscore_exit=$?
  printf '{"roscore_pid":%s,"map_pid":"%s","launch_pid":"%s","capture_pid":"%s","monitor_pid":"%s","roscore_exit":%s,"map_exit":%s,"launch_exit":%s,"capture_exit":%s,"monitor_exit":%s}\n' "$roscore_pid" "$map_pid" "$launch_pid" "$capture_pid" "$monitor_pid" "$roscore_exit" "$map_exit" "$launch_exit" "$capture_exit" "$monitor_exit" >"$run_dir/processes.json"
}
trap cleanup EXIT

for attempt in $(seq 1 30); do
  env PYTHONPATH="$ros_pythonpath" /opt/ros/noetic/bin/rosparam list >/dev/null 2>&1 && break
  sleep 1
done
env PYTHONPATH="$ros_pythonpath" /opt/ros/noetic/bin/rosparam list >/dev/null
env PYTHONPATH="$ros_pythonpath" /usr/bin/python3 "$capture_script" --output-dir "$run_dir" --timeout-s "$timeout_s" >"$run_dir/capture.log" 2>&1 & capture_pid=$!
env PYTHONPATH='' /usr/bin/python3 "$monitor_script" --run-dir "$run_dir" --timeout-s "$timeout_s" >"$run_dir/monitor.log" 2>&1 & monitor_pid=$!
sleep 2
cd "$workspace/src"
env PYTHONPATH="$ros_pythonpath" /home/amplanner/miniforge3/envs/am-planner-py38/bin/python "$workspace/src/map/desk.py" >"$run_dir/map.log" 2>&1 & map_pid=$!
env PYTHONHOME="$conda_root" PYTHONPATH="$gpu_pythonpath" "$conda_root/bin/python" /opt/ros/noetic/bin/roslaunch --screen "$launch_file" >"$run_dir/roslaunch.log" 2>&1 & launch_pid=$!
sleep 5
env PYTHONPATH="$ros_pythonpath" /opt/ros/noetic/bin/rosnode list >"$run_dir/rosnode_list.txt" || true
env PYTHONPATH="$ros_pythonpath" /opt/ros/noetic/bin/rostopic list >"$run_dir/rostopic_list.txt" || true
env PYTHONPATH="$ros_pythonpath" /opt/ros/noetic/bin/rostopic type /trajectory >"$run_dir/trajectory_type.txt" || true
env PYTHONPATH="$ros_pythonpath" /opt/ros/noetic/bin/rostopic type /trajectory_arm >"$run_dir/trajectory_arm_type.txt" || true
set +e
wait "$capture_pid"
capture_status=$?
set -e
printf '{"task":"grasp_waypoint_variant","run_id":"%s","capture_exit":%s}\n' "$run_id" "$capture_status" >"$run_dir/result_summary.json"
exit "$capture_status"
