param(
  [Parameter(Mandatory)][ValidateSet('grasp','write','lift')][string]$Task,
  [Parameter(Mandatory)][string]$RunId,
  [int]$TimeoutSeconds = 180
)

$taskRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$wslRoot = (wsl -d AMPlanner-Ubuntu20 --exec wslpath -a (Convert-Path $taskRoot)).Trim()
if ([string]::IsNullOrWhiteSpace($wslRoot)) {
  throw "Unable to translate the project path for AMPlanner-Ubuntu20."
}
$runner = "$wslRoot/scripts/reproduce/s1_r1_run_am_planner_basic.sh"
$capture = "$wslRoot/scripts/reproduce/s1_r1_capture_ros_message.py"
$outputRoot = '/home/amplanner/am-planner-ws/logs/s1-r1-runtime'
$started = (Get-Date).ToUniversalTime().ToString('o')
wsl -d AMPlanner-Ubuntu20 -- timeout "$TimeoutSeconds" bash -lc "tr -d '\r' < '$runner' | bash -s -- '$Task' '$RunId' '$outputRoot' '$capture'"
$exitCode = $LASTEXITCODE
[pscustomobject]@{ task=$Task; run_id=$RunId; started_utc=$started; timeout_seconds=$TimeoutSeconds; wsl_exit=$exitCode } |
  ConvertTo-Json -Compress
exit $exitCode
