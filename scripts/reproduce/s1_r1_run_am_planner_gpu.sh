#!/usr/bin/env bash
# Run one official AM-Planner task in the isolated GPU Catkin workspace.
set -eo pipefail

task=${1:?usage: s1_r1_run_am_planner_gpu.sh grasp|write|lift run-id output-root capture-script monitor-script timeout-s}
run_id=${2:?run id required}
output_root=${3:?output root required}
capture_script=${4:?capture script path required}
monitor_script=${5:?monitor script path required}
timeout_s=${6:?timeout seconds required}
case "$task" in grasp|write|lift) ;; *) echo "unsupported task: $task" >&2; exit 64 ;; esac

run_dir="$output_root/$run_id"
mkdir -p "$run_dir"
exec > "$run_dir/runner.log" 2>&1
source /home/amplanner/miniforge3/etc/profile.d/conda.sh
conda activate am-planner-gpu-probe-py39
source /opt/ros/noetic/setup.bash
source /home/amplanner/am-planner-gpu-ws/devel/setup.bash
ROS_PYTHONPATH="/home/amplanner/am-planner-gpu-ws/devel/lib/python3/dist-packages:/opt/ros/noetic/lib/python3/dist-packages:/usr/lib/python3/dist-packages"
GPU_PYTHONPATH="$CONDA_PREFIX/lib/python3.9/site-packages:$ROS_PYTHONPATH"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$CONDA_PREFIX/lib/python3.9/site-packages/torch/lib:/opt/ros/noetic/lib:${LD_LIBRARY_PATH:-}"
runtime_bin="$run_dir/runtime-bin"
mkdir -p "$runtime_bin"
ln -sf "$(dirname "$capture_script")/s1_r1_rosversion_gpu_wrapper.sh" "$runtime_bin/rosversion"
export PATH="$runtime_bin:$PATH"
export SE3_WRAPPER_LOG="$run_dir/se3_wrapper_environment.txt"
se3_bin=/home/amplanner/am-planner-gpu-ws/devel/.private/plan_manage/lib/plan_manage/se3_node
se3_real="$se3_bin.gpu_real"
if [[ ! -e "$se3_real" ]]; then mv "$se3_bin" "$se3_real"; fi
cp "$(dirname "$capture_script")/s1_r1_se3_gpu_wrapper.sh" "$se3_bin"
chmod +x "$se3_bin"
printf '%s\n' "runtime wrapper installed; original binary restored on cleanup" > "$run_dir/se3_wrapper_used.txt"
export ROS_HOME="$run_dir/ros_home"
export MPLBACKEND=Agg
mkdir -p "$ROS_HOME"

printf '%s\n' "task=$task" "run_id=$run_id" "timeout_s=$timeout_s" "started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$run_dir/command.txt"
env | sort > "$run_dir/environment.txt"
printf '%s\n' "$(python --version 2>&1)" "$(python -c 'import torch; print(torch.__version__); print(torch.cuda.is_available())')" > "$run_dir/gpu_runtime_python.txt"

env PYTHONPATH="$ROS_PYTHONPATH" /opt/ros/noetic/bin/roscore > "$run_dir/roscore.log" 2>&1 &
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
    "$roscore_pid" "$map_pid" "$launch_pid" "$capture_pid" "$monitor_pid" "$roscore_exit" "$map_exit" "$launch_exit" "$capture_exit" "$monitor_exit" > "$run_dir/processes.json"
  printf 'cleanup_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$run_dir/cleanup_log.txt"
  if [[ -e "$se3_real" ]]; then rm -f "$se3_bin"; mv "$se3_real" "$se3_bin"; fi
}
trap cleanup EXIT

for attempt in $(seq 1 30); do
  if env PYTHONPATH="$ROS_PYTHONPATH" /opt/ros/noetic/bin/rosparam list >/dev/null 2>&1; then break; fi
  sleep 1
done
env PYTHONPATH="$ROS_PYTHONPATH" /opt/ros/noetic/bin/rosparam list >/dev/null

env PYTHONPATH="$ROS_PYTHONPATH" /usr/bin/python3 "$capture_script" --output-dir "$run_dir" --timeout-s "$timeout_s" > "$run_dir/capture.log" 2>&1 &
capture_pid=$!
env PYTHONPATH="" /usr/bin/python3 "$monitor_script" --run-dir "$run_dir" --timeout-s "$timeout_s" > "$run_dir/monitor.log" 2>&1 &
monitor_pid=$!
sleep 2

cd /home/amplanner/am-planner-gpu-ws/src/am-planner
env PYTHONPATH="$ROS_PYTHONPATH" /home/amplanner/miniforge3/envs/am-planner-py38/bin/python /home/amplanner/am-planner-ws/src/am-planner/map/desk.py > "$run_dir/map.log" 2>&1 &
map_pid=$!
if [[ "$task" == grasp ]]; then
  env PYTHONHOME="$CONDA_PREFIX" PYTHONPATH="$GPU_PYTHONPATH" "$CONDA_PREFIX/bin/python" /opt/ros/noetic/bin/roslaunch --screen plan_manage run_in_sim_grasp.launch > "$run_dir/roslaunch.log" 2>&1 &
else
  env PYTHONHOME="$CONDA_PREFIX" PYTHONPATH="$GPU_PYTHONPATH" "$CONDA_PREFIX/bin/python" /opt/ros/noetic/bin/roslaunch --screen plan_manage run_in_sim_other.launch "task:=$task" > "$run_dir/roslaunch.log" 2>&1 &
fi
launch_pid=$!

sleep 5
env PYTHONPATH="$ROS_PYTHONPATH" /opt/ros/noetic/bin/rosnode list > "$run_dir/rosnode_list.txt" || true
env PYTHONPATH="$ROS_PYTHONPATH" /opt/ros/noetic/bin/rostopic list > "$run_dir/rostopic_list.txt" || true
env PYTHONPATH="$ROS_PYTHONPATH" /opt/ros/noetic/bin/rostopic type /trajectory > "$run_dir/trajectory_type.txt" || true
env PYTHONPATH="$ROS_PYTHONPATH" /opt/ros/noetic/bin/rostopic type /trajectory_arm > "$run_dir/trajectory_arm_type.txt" || true

set +e
wait "$capture_pid"
capture_status=$?
set -e
printf '{"task":"%s","run_id":"%s","capture_exit":%s,"finished_utc":"%s"}\n' \
  "$task" "$run_id" "$capture_status" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$run_dir/result_summary.json"
cd /home/amplanner/am-planner-gpu-ws/src/am-planner
git status --short > "$run_dir/source_git_state_after.txt"
exit "$capture_status"
