#!/usr/bin/env bash
# One controlled write run plus low-interference monitor. No upstream files are changed.
set -u

task_root=${1:?task root}; output_root=${2:?output root}; run_id=${3:?run id}
capture_timeout=${4:-1200}
runner="$task_root/scripts/reproduce/s1_r1_run_with_cpu_weight.sh"
basic="$task_root/scripts/reproduce/s1_r1_run_am_planner_basic.sh"
capture="$task_root/scripts/reproduce/s1_r1_capture_ros_message.py"
monitor="$task_root/scripts/reproduce/s1_r1_monitor_write_process.py"
source_root=/home/amplanner/am-planner-ws/src/am-planner
run_dir="$output_root/$run_id"
mkdir -p "$run_dir"
printf '%s\n' "roslaunch plan_manage run_in_sim_other.launch task:=write" "capture_timeout_s=$capture_timeout" "started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$run_dir/command.txt"
printf '%s\n' "CPU model bind mount is provided only by the existing wrapper; no permanent weight replacement." > "$run_dir/workaround_mode.txt"
monitor_python=/home/amplanner/miniforge3/envs/am-planner-py38/bin/python
"$monitor_python" "$monitor" --run-dir "$run_dir" --timeout-s "$capture_timeout" > "$run_dir/monitor_launcher.log" 2>&1 &
monitor_pid=$!
export S1_R1_CAPTURE_TIMEOUT="$capture_timeout"
tr -d '\r' < "$runner" | bash -s -- write "$run_id" "$output_root" "$capture" "$basic" "$source_root" > "$run_dir/runner_launcher.log" 2>&1
runner_status=$?
wait "$monitor_pid" 2>/dev/null || true
printf '%s\n' "runner_exit=$runner_status" "finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$run_dir/command.txt"
exit "$runner_status"
