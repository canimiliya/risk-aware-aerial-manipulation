param([string]$OutputDir = (Join-Path $PSScriptRoot '..\..\docs\evidence\S0-R1'))
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
function Version-Or([string]$Command, [string[]]$Args) {
  $cmd = Get-Command $Command -ErrorAction SilentlyContinue
  if (-not $cmd) { return 'NOT_INSTALLED' }
  try { return ((& $Command @Args 2>&1 | Select-Object -First 1) -join ' ').Trim() } catch { return 'NOT_VERIFIED' }
}
$os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture
$cpu = Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed
$memory = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
$disks = @(Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | Select-Object DeviceID,FileSystem,Size,FreeSpace)
$gpu = 'NOT_VERIFIED'; if(Get-Command nvidia-smi -ErrorAction SilentlyContinue){$gpu=((nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap --format=csv,noheader 2>$null) -join '; ')}
$wslStatus = if(Get-Command wsl -ErrorAction SilentlyContinue){'WSL_AVAILABLE'}else{'NOT_INSTALLED'}
$long = try { ((reg query HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled 2>$null) -join ' ') } catch {'NOT_VERIFIED'}
$audit = [ordered]@{audit_date=(Get-Date -Format 'yyyy-MM-dd'); os=$os; cpu=$cpu; memory_bytes=$memory; gpu=$gpu; disks=$disks; wsl=@{status=$wslStatus}; python=(Version-Or 'python' @('--version')); conda=(Version-Or 'conda' @('--version')); git=(Version-Or 'git' @('--version')); gh=(Version-Or 'gh' @('--version')); long_paths=$long; unknowns=@('CUDA Toolkit exact status requires nvcc lookup','WSL distribution suitability for ROS Noetic is not verified in S0')}
$audit | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $OutputDir 'hardware_audit.json')
@("OS: $($os.Caption) $($os.Version) build $($os.BuildNumber)","CPU: $($cpu.Name); cores $($cpu.NumberOfCores); logical $($cpu.NumberOfLogicalProcessors)","RAM bytes: $memory","GPU: $gpu") | Set-Content -Encoding UTF8 (Join-Path $OutputDir 'hardware_summary.txt')
@("Python: $(Version-Or 'python' @('--version'))","Conda: $(Version-Or 'conda' @('--version'))","Git: $(Version-Or 'git' @('--version'))","gh: $(Version-Or 'gh' @('--version'))","CMake: $(Version-Or 'cmake' @('--version'))","Ninja: $(Version-Or 'ninja' @('--version'))","Docker: $(Version-Or 'docker' @('--version'))") | Set-Content -Encoding UTF8 (Join-Path $OutputDir 'toolchain_summary.txt')
@("$wslStatus",((wsl --list --verbose 2>$null) -join "`n")) | Set-Content -Encoding UTF8 (Join-Path $OutputDir 'wsl_summary.txt')
@($disks | ForEach-Object { "$($_.DeviceID) $($_.FileSystem) free=$($_.FreeSpace) size=$($_.Size)" }) + "LongPaths: $long" | Set-Content -Encoding UTF8 (Join-Path $OutputDir 'path_and_disk_summary.txt')
