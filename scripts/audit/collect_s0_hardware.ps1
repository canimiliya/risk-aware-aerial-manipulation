param([string]$OutputDir = (Join-Path $PSScriptRoot '..\..\docs\evidence\S0-R1-R1'))
$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$log = [System.Collections.Generic.List[string]]::new()
function Run-Tool([string]$Name, [string[]]$ToolArgs) {
  $cmd = Get-Command $Name -ErrorAction SilentlyContinue
  $path = if($Name -eq 'conda'){((& where.exe conda 2>$null)|Where-Object {$_ -match '\.exe$'}|Select-Object -First 1)}elseif($cmd -and $cmd.Source){$cmd.Source}else{((& where.exe $Name 2>$null)|Select-Object -First 1)}
  if(-not $cmd){$log.Add("$Name $($ToolArgs -join ' ') | exit=NOT_INSTALLED"); return [ordered]@{status='NOT_INSTALLED';path=$null;version_output='NOT_INSTALLED';exit_code=$null}}
  try {
    $out=@(& $path @ToolArgs 2>&1 | ForEach-Object {[string]$_});$code=if($null -eq $LASTEXITCODE){0}else{$LASTEXITCODE};$joined=($out -join "`n").Trim()
    if($code -ne 0){$status='COMMAND_FAILED'}elseif($joined -match '(?im)^\s*usage:'){ $status='COMMAND_FAILED'}else{$status='OK'}
    $log.Add("$Name $($ToolArgs -join ' ') | exit=$code | status=$status")
    return [ordered]@{status=$status;path=$path;version_output=$joined;exit_code=$code}
  } catch { $log.Add("$Name $($ToolArgs -join ' ') | exit=COMMAND_FAILED | $_"); return [ordered]@{status='COMMAND_FAILED';path=$path;version_output=[string]$_;exit_code=$null} }
}
function Write-Utf8NoBom([string]$Path,[string]$Text){[IO.File]::WriteAllText($Path,$Text,(New-Object Text.UTF8Encoding($false)))}
$os=Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture
$cpu=Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed
$memory=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
$disks=@(Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | Select-Object DeviceID,FileSystem,Size,FreeSpace)
$nvidiaPath=(Get-Command nvidia-smi -ErrorAction SilentlyContinue).Source
$nvidiaQuery='NOT_INSTALLED';$nvidiaTop='NOT_INSTALLED';$nvidiaExit=$null
if($nvidiaPath){$nvidiaQuery=((& nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap --format=csv,noheader 2>&1)|ForEach-Object {[string]$_}) -join "`n";$nvidiaExit=$LASTEXITCODE;$nvidiaTop=((& nvidia-smi 2>&1)|ForEach-Object {[string]$_}) -join "`n";$nvidiaTop=($nvidiaTop -split "`n" | Select-Object -First 12) -join "`n"}
Write-Utf8NoBom (Join-Path $OutputDir 'nvidia_smi.txt') ("QUERY exit=$nvidiaExit`n$nvidiaQuery`n`nTOP_SUMMARY exit=$nvidiaExit`n$nvidiaTop")
$tools=[ordered]@{python=(Run-Tool -Name 'python' -ToolArgs @('--version'));conda=(Run-Tool -Name 'conda' -ToolArgs @('--version'));git=(Run-Tool -Name 'git' -ToolArgs @('--version'));gh=(Run-Tool -Name 'gh' -ToolArgs @('--version'));cmake=(Run-Tool -Name 'cmake' -ToolArgs @('--version'));ninja=(Run-Tool -Name 'ninja' -ToolArgs @('--version'));docker=(Run-Tool -Name 'docker' -ToolArgs @('--version'));nvcc=(Run-Tool -Name 'nvcc' -ToolArgs @('--version'))}
$long=(reg query HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled 2>&1 | ForEach-Object {[string]$_}) -join ' '
$wslStatus=[ordered]@{status='CAPTURED_BY_TIMEOUT_GUARD';path=(Get-Command wsl -ErrorAction SilentlyContinue).Source;version_output='See wsl_status_utf8.txt';exit_code=$null}
$wslVersion=[ordered]@{status='CAPTURED_BY_TIMEOUT_GUARD';path=(Get-Command wsl -ErrorAction SilentlyContinue).Source;version_output='See wsl_version_utf8.txt';exit_code=$null}
$wslList=[ordered]@{status='CAPTURED_BY_TIMEOUT_GUARD';path=(Get-Command wsl -ErrorAction SilentlyContinue).Source;version_output='See wsl_list_verbose_utf8.txt';exit_code=$null}
function Capture-Wsl([string]$Name,[string[]]$Args){
  $tmp=Join-Path $OutputDir ("$Name.tmp"); $target=Join-Path $OutputDir ("$Name.txt"); $cmdline="wsl.exe $($Args -join ' ') > `"$tmp`" 2>&1"
  $proc=Start-Process -FilePath 'cmd.exe' -ArgumentList @('/u','/c',$cmdline) -WindowStyle Hidden -PassThru
  if($proc.WaitForExit(5000)){$code=$proc.ExitCode}else{$proc.Kill();$proc.WaitForExit();$code='COMMAND_TIMEOUT'}
  try{$text=[IO.File]::ReadAllText($tmp,[Text.Encoding]::Unicode)}catch{$text='COMMAND_FAILED: '+$_}
  if(Test-Path $tmp){Remove-Item -LiteralPath $tmp -Force}
  Write-Utf8NoBom $target $text.TrimEnd();$log.Add("wsl $($Args -join ' ') | exit=$code | file=$Name.txt");return $code
}
$wslStatusCode='DEFERRED_TO_CONTROLLED_WSL_PROBE';$wslVersionCode=$wslStatusCode;$wslListCode=$wslStatusCode;$airCode=$wslStatusCode
foreach($n in @('wsl_status_utf8','wsl_version_utf8','wsl_list_verbose_utf8','AirFAR-Ubuntu20_os_release')){if(-not(Test-Path (Join-Path $OutputDir "$n.txt"))){Write-Utf8NoBom (Join-Path $OutputDir "$n.txt") 'CONTROLLED_PROBE_PENDING'}}
$audit=[ordered]@{audit_date=(Get-Date -Format 'yyyy-MM-dd');project_root=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path;os=$os;cpu=$cpu;memory_bytes=$memory;gpu=[ordered]@{query=$nvidiaQuery;compute_capability=($nvidiaQuery -split ',')[-1].Trim();driver_cuda_compatibility=(($nvidiaTop -split "`n"|Where-Object {$_ -match 'CUDA Version'}) -join ' ');nvidia_smi_exit_code=$nvidiaExit};disks=$disks;wsl=[ordered]@{status=$wslStatus;version=$wslVersion;list_verbose=$wslList};python=$tools.python;conda=$tools.conda;git=$tools.git;gh=$tools.gh;cmake=$tools.cmake;ninja=$tools.ninja;docker=$tools.docker;cuda_toolkit=$tools.nvcc;long_paths=$long;unknowns=@('ROS Noetic readiness not verified','Isaac Lab not installed')}
$json=$audit|ConvertTo-Json -Depth 8;Write-Utf8NoBom (Join-Path $OutputDir 'hardware_audit.json') $json
Write-Utf8NoBom (Join-Path $OutputDir 'toolchain_raw.txt') (($tools.GetEnumerator()|ForEach-Object {"[$($_.Key)]`n$($_.Value.version_output)`npath=$($_.Value.path) status=$($_.Value.status) exit=$($_.Value.exit_code)"}) -join "`n")
Write-Utf8NoBom (Join-Path $OutputDir 'toolchain_summary.txt') (($tools.GetEnumerator()|ForEach-Object {"$($_.Key): status=$($_.Value.status), version=$($_.Value.version_output.Split("`n")[0]), path=$($_.Value.path), exit=$($_.Value.exit_code)"}) -join "`n")
Write-Utf8NoBom (Join-Path $OutputDir 'path_and_disk_summary.txt') ((@($disks|ForEach-Object {"$($_.DeviceID) total=$($_.Size) free=$($_.FreeSpace) fs=$($_.FileSystem)"})+"LongPathsEnabled: $long") -join "`n")
Write-Utf8NoBom (Join-Path $OutputDir 'collection_log.txt') (($log+"nvidia-smi query exit=$nvidiaExit"+"wsl status/version/list/air os-release exits=$wslStatusCode/$wslVersionCode/$wslListCode/$airCode") -join "`n")
if($nvidiaExit -ne 0){exit 1}
