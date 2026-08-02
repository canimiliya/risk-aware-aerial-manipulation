#!/usr/bin/env bash
set -euo pipefail

task="${1:?usage: s1_r1_run_r7r3_r1_gpu.sh write|grasp|lift run-id timeout-s}"
run_id="${2:?run id required}"
timeout_s="${3:?timeout seconds required}"
case "$task" in write|grasp|lift) ;; *) echo "unsupported task: $task" >&2; exit 64 ;; esac

workspace=/home/amplanner/am-planner-r7r3-r1-ws
overlay=/home/amplanner/ros-noetic-py39-overlay-r7r3-r1
conda_root=/home/amplanner/miniforge3/envs/am-planner-gpu-probe-py39
output_root="$workspace/runs"
run_dir="$output_root/$run_id"
capture_script=/mnt/d/Desktop/my_project/Simulation_Research_on_Aerial_Manipulator_for_Power_Line_Bird_Diverter_Operation/scripts/reproduce/s1_r1_capture_ros_message.py
monitor_script=/mnt/d/Desktop/my_project/Simulation_Research_on_Aerial_Manipulator_for_Power_Line_Bird_Diverter_Operation/scripts/reproduce/s1_r1_monitor_gpu_planner.py

mkdir -p "$run_dir"
exec >"$run_dir/runner.log" 2>&1
exec 9>/tmp/s1-r1-r7r3-r1-gpu.lock
flock -n 9

source /home/amplanner/miniforge3/etc/profile.d/conda.sh
conda activate am-planner-gpu-probe-py39
export ROS_DISTRO=noetic
export ROS_VERSION=1
export ROS_MASTER_URI=http://localhost:11311
source /opt/ros/noetic/setup.bash
source "$overlay/devel/setup.bash"
source "$workspace/devel/setup.bash"

export PATH="$conda_root:/opt/ros/noetic/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/lib/wsl/lib"
ROS_PYTHONPATH="$workspace/devel/lib/python3/dist-packages:$overlay/devel/lib/python3/dist-packages:/opt/ros/noetic/lib/python3/dist-packages:/usr/lib/python3/dist-packages"
GPU_PYTHONPATH="$conda_root/lib/python3.9/site-packages:$ROS_PYTHONPATH"
export LD_LIBRARY_PATH="$workspace/devel/lib:$overlay/devel/lib:$conda_root/lib:$conda_root/lib/python3.9/site-packages/torch/lib:/opt/ros/noetic/lib:/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu"
export ROS_HOME="$run_dir/ros_home"
export MPLBACKEND=Agg
export ROS_PACKAGE_PATH="$workspace/src:$overlay/src:/opt/ros/noetic/share"
mkdir -p "$ROS_HOME"
runtime_bin="$run_dir/runtime-bin"
mkdir -p "$runtime_bin"
ln -sf /mnt/d/Desktop/my_project/Simulation_Research_on_Aerial_Manipulator_for_Power_Line_Bird_Diverter_Operation/scripts/reproduce/s1_r1_rosversion_r7r3_r1_wrapper.sh "$runtime_bin/rosversion"
export PATH="$runtime_bin:$PATH"

{
  printf '%s\n' "task=$task" "run_id=$run_id" "timeout_s=$timeout_s" "workspace=$workspace" "overlay=$overlay" "started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '%s\n' '---python---'
  "$conda_root/bin/python" --version
  "$conda_root/bin/python" -c 'import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print(torch.cuda.get_device_capability(0))'
  printf '%s\n' '---nvidia-smi---'
  nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
} >"$run_dir/command.txt"
env | sort >"$run_dir/environment.txt"

env PYTHONPATH="$ROS_PYTHONPATH" /opt/ros/noetic/bin/roscore >"$run_dir/roscore.log" 2>&1 &
roscore_pid=$!
launch_pid=''
map_pid=''
capture_pid=''
monitor_pid=''

cleanup() {
  set +e
  for pid in "$launch_pid" "$map_pid" "$capture_pid" "$monitor_pid" "$roscore_pid"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then kill "$pid" 2>/dev/null; fi
  done
  wait "$launch_pid" 2>/dev/null; launch_exit=$?
  wait "$map_pid" 2>/dev/null; map_exit=$?
  wait "$capture_pid" 2>/dev/null; capture_exit=$?
  wait "$monitor_pid" 2>/dev/null; monitor_exit=$?
  wait "$roscore_pid" 2>/dev/null; roscore_exit=$?
  printf '{"roscore_pid":%s,"map_pid":"%s","launch_pid":"%s","capture_pid":"%s","monitor_pid":"%s","roscore_exit":%s,"map_exit":%s,"launch_exit":%s,"capture_exit":%s,"monitor_exit":%s}\n' \
    "$roscore_pid" "$map_pid" "$launch_pid" "$capture_pid" "$monitor_pid" "$roscore_exit" "$map_exit" "$launch_exit" "$capture_exit" "$monitor_exit" >"$run_dir/processes.json"
  printf 'cleanup_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$run_dir/cleanup_log.txt"
}
trap cleanup EXIT

for attempt in $(seq 1 30); do
  if env PYTHONPATH="$ROS_PYTHONPATH" /opt/ros/noetic/bin/rosparam list >/dev/null 2>&1; then break; fi
  sleep 1
done
env PYTHONPATH="$ROS_PYTHONPATH" /opt/ros/noetic/bin/rosparam list >/dev/null

env PYTHONPATH="$ROS_PYTHONPATH" /usr/bin/python3 "$capture_script" --output-dir "$run_dir" --timeout-s "$timeout_s" >"$run_dir/capture.log" 2>&1 &
capture_pid=$!
env PYTHONPATH='' /usr/bin/python3 "$monitor_script" --run-dir "$run_dir" --timeout-s "$timeout_s" >"$run_dir/monitor.log" 2>&1 &
monitor_pid=$!
sleep 2

cd "$workspace/src"
env PYTHONPATH="$ROS_PYTHONPATH" /home/amplanner/miniforge3/envs/am-planner-py38/bin/python "$workspace/src/map/desk.py" >"$run_dir/map.log" 2>&1 &
map_pid=$!
if [[ "$task" == grasp ]]; then
  env PYTHONHOME="$conda_root" PYTHONPATH="$GPU_PYTHONPATH" "$conda_root/bin/python" /opt/ros/noetic/bin/roslaunch --screen plan_manage run_in_sim_grasp.launch >"$run_dir/roslaunch.log" 2>&1 &
else
  env PYTHONHOME="$conda_root" PYTHONPATH="$GPU_PYTHONPATH" "$conda_root/bin/python" /opt/ros/noetic/bin/roslaunch --screen plan_manage run_in_sim_other.launch "task:=$task" >"$run_dir/roslaunch.log" 2>&1 &
fi
launch_pid=$!

sleep 5
env PYTHONPATH="$ROS_PYTHONPATH" /opt/ros/noetic/bin/rosnode list >"$run_dir/rosnode_list.txt" || true
env PYTHONPATH="$ROS_PYTHONPATH" /opt/ros/noetic/bin/rostopic list >"$run_dir/rostopic_list.txt" || true
env PYTHONPATH="$ROS_PYTHONPATH" /opt/ros/noetic/bin/rostopic type /trajectory >"$run_dir/trajectory_type.txt" || true
env PYTHONPATH="$ROS_PYTHONPATH" /opt/ros/noetic/bin/rostopic type /trajectory_arm >"$run_dir/trajectory_arm_type.txt" || true

set +e
wait "$capture_pid"
capture_status=$?
set -e
printf '{"task":"%s","run_id":"%s","capture_exit":%s,"finished_utc":"%s"}\n' \
  "$task" "$run_id" "$capture_status" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$run_dir/result_summary.json"
exit "$capture_status"
