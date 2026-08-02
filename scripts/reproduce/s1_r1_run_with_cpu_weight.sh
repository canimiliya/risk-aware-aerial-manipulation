#!/usr/bin/env bash
# Temporarily present a CPU-normalized checkpoint at AM-Planner's fixed path.
set -euo pipefail

task=${1:?task}; run_id=${2:?run id}; output_root=${3:?output root}; capture_script=${4:?capture}; basic_runner=${5:?basic runner}; source_root=${6:?source root}
# PowerShell-to-WSL pipes can retain a carriage return in the final argument.
for name in task run_id output_root capture_script basic_runner source_root; do
  value=${!name//$'\r'/}
  printf -v "$name" '%s' "$value"
done
original="$source_root/src/plan/traj_opt/weights/workspace_probability_weight.pth"
converted=/home/amplanner/am-planner-ws/runtime_assets/workspace_probability_weight_cpu.pth
run_dir="$output_root/$run_id"
mkdir -p "$run_dir"
mounted=0

cleanup() {
  set +e
  if [[ "$mounted" == 1 ]]; then sudo -n umount "$original"; fi
  {
    echo "cleanup_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    findmnt -T "$original" || true
    sha256sum "$original" || true
    cd "$source_root" && git status --short || true
  } >> "$run_dir/cleanup_log.txt"
}
trap cleanup EXIT INT TERM

{
  echo 'BIND_MOUNT_CPU_WEIGHT'
  echo "original_before=$(sha256sum "$original")"
  echo "converted=$(sha256sum "$converted")"
  findmnt -T "$original" || true
} > "$run_dir/mount_or_shim_probe.txt"
sudo -n mount --bind "$converted" "$original"
mounted=1
{
  echo "mounted_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  findmnt -T "$original"
  sha256sum "$original"
} >> "$run_dir/mount_or_shim_probe.txt"
export S1_R1_WORKAROUND_MODE=BIND_MOUNT_CPU_WEIGHT
tr -d '\r' < "$basic_runner" | bash -s -- "$task" "$run_id" "$output_root" "$capture_script"
