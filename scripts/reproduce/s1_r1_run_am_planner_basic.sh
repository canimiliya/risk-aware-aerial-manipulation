#!/usr/bin/env bash
# Run one official AM-Planner basic task in an isolated ROS session.
set -eo pipefail

task=${1:?usage: s1_r1_run_am_planner_basic.sh grasp|write|lift run-id output-root capture-script}
run_id=${2:?run id required}
output_root=${3:?output root required}
capture_script=${4:?capture script path required}

case "$task" in grasp|write|lift) ;; *) echo "unsupported task: $task" >&2; exit 64 ;; esac

run_dir="$output_root/$run_id"
mkdir -p "$run_dir"
exec > "$run_dir/runner.log" 2>&1

source /home/amplanner/miniforge3/etc/profile.d/conda.sh
conda activate am-planner-py38
export CMAKE_PREFIX_PATH=/home/amplanner/miniforge3/envs/am-planner-py38:/opt/ros/noetic
source /opt/ros/noetic/setup.bash
source /home/amplanner/am-planner-ws/devel/setup.bash
set -u
export ROS_HOME="$run_dir/ros_home"
export MPLBACKEND=Agg
mkdir -p "$ROS_HOME"

printf '%s\n' "task=$task" "run_id=$run_id" "started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$run_dir/command.txt"
env | sort > "$run_dir/environment.txt"

roscore > "$run_dir/roscore.log" 2>&1 &
roscore_pid=$!
launch_pid=''
map_pid=''
capture_pid=''

cleanup() {
  set +e
  for pid in "$launch_pid" "$map_pid" "$capture_pid" "$roscore_pid"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then kill "$pid" 2>/dev/null; fi
  done
  wait "$launch_pid" 2>/dev/null; launch_exit=$?
  wait "$map_pid" 2>/dev/null; map_exit=$?
  wait "$capture_pid" 2>/dev/null; capture_exit=$?
  wait "$roscore_pid" 2>/dev/null; roscore_exit=$?
  printf '{"roscore_pid":%s,"map_pid":"%s","launch_pid":"%s","capture_pid":"%s","roscore_exit":%s,"map_exit":%s,"launch_exit":%s,"capture_exit":%s}\n' \
    "$roscore_pid" "$map_pid" "$launch_pid" "$capture_pid" "$roscore_exit" "$map_exit" "$launch_exit" "$capture_exit" > "$run_dir/processes.json"
  printf 'cleanup_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$run_dir/cleanup_log.txt"
}
trap cleanup EXIT

for attempt in $(seq 1 30); do
  if rosparam list >/dev/null 2>&1; then break; fi
  sleep 1
done
rosparam list >/dev/null

python "$capture_script" --output-dir "$run_dir" --timeout-s 150 > "$run_dir/capture.log" 2>&1 &
capture_pid=$!
sleep 2

cd /home/amplanner/am-planner-ws/src/am-planner
python map/desk.py > "$run_dir/map.log" 2>&1 &
map_pid=$!
if [[ "$task" == grasp ]]; then
  roslaunch --screen plan_manage run_in_sim_grasp.launch > "$run_dir/roslaunch.log" 2>&1 &
else
  roslaunch --screen plan_manage run_in_sim_other.launch "task:=$task" > "$run_dir/roslaunch.log" 2>&1 &
fi
launch_pid=$!

sleep 5
rosnode list > "$run_dir/rosnode_list.txt" || true
rostopic list > "$run_dir/rostopic_list.txt" || true
rostopic type /trajectory > "$run_dir/trajectory_type.txt" || true
rostopic type /trajectory_arm > "$run_dir/trajectory_arm_type.txt" || true

set +e
wait "$capture_pid"
capture_status=$?
set -e
printf '{"task":"%s","run_id":"%s","capture_exit":%s,"finished_utc":"%s"}\n' \
  "$task" "$run_id" "$capture_status" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$run_dir/result_summary.json"
exit "$capture_status"
