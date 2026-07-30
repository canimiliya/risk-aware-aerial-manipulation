param(
    [string]$OutputDir = (Join-Path (Split-Path -Parent $PSScriptRoot) '..\\docs\\evidence\\S1-R0'),
    [int]$TimeoutSeconds = 45
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputDir = [IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

function Invoke-RecordedCommand {
    param([string]$Name, [string]$FileName, [string[]]$Arguments, [int]$Timeout = $TimeoutSeconds)
    $started = (Get-Date).ToUniversalTime().ToString('o')
    $p = [Diagnostics.Process]::new()
    $p.StartInfo.FileName = $FileName
    $p.StartInfo.Arguments = [string]::Join(' ', ($Arguments | ForEach-Object { if ($_ -match '[\s"]') { '"' + ($_ -replace '"','\\"') + '"' } else { $_ } }))
    $p.StartInfo.UseShellExecute = $false
    $p.StartInfo.RedirectStandardOutput = $true
    $p.StartInfo.RedirectStandardError = $true
    $p.StartInfo.StandardOutputEncoding = [Text.UTF8Encoding]::new($false)
    $p.StartInfo.StandardErrorEncoding = [Text.UTF8Encoding]::new($false)
    [void]$p.Start()
    $stdoutTask = $p.StandardOutput.ReadToEndAsync(); $stderrTask = $p.StandardError.ReadToEndAsync()
    $timedOut = -not $p.WaitForExit($Timeout * 1000)
    if ($timedOut) { try { $p.Kill() } catch {} ; $p.WaitForExit() }
    $result = [ordered]@{ name=$Name; command=($FileName + ' ' + $p.StartInfo.Arguments); started_utc=$started; ended_utc=(Get-Date).ToUniversalTime().ToString('o'); exit_code=if($timedOut){$null}else{$p.ExitCode}; timed_out=$timedOut; stdout=$stdoutTask.Result; stderr=$stderrTask.Result }
    $result | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $OutputDir ($Name + '.json')) -Encoding utf8
    return [PSCustomObject]$result
}

$hostCommands = @(
    @{n='wsl_version'; a=@('--version')}, @{n='wsl_status'; a=@('--status')},
    @{n='wsl_list_verbose'; a=@('--list','--verbose')}, @{n='wsl_list_running'; a=@('--list','--running')}
)
$hostResults = foreach($c in $hostCommands){ Invoke-RecordedCommand -Name $c.n -FileName 'wsl.exe' -Arguments $c.a }
$knownDistros = @('Ubuntu-24.04','Ubuntu','NMPC-Ubuntu22','dbLaCAM-Ubuntu','AirFAR-Ubuntu20')
$listed = (($hostResults | Where-Object name -eq 'wsl_list_verbose').stdout -replace "`0", '')
foreach($distro in $knownDistros) {
    if ($listed -match [regex]::Escape($distro)) {
        $probe = @'
set -o pipefail; echo '=== os-release ==='; cat /etc/os-release 2>/dev/null || true; echo '=== uname ==='; uname -a; echo '=== user ==='; id; echo '=== home ==='; printf '%s\n' "$HOME"; echo '=== disk ==='; df -h / /home 2>/dev/null || true; echo '=== python ==='; python3 --version 2>&1 || true; echo '=== git ==='; git --version 2>&1 || true; echo '=== ros ==='; printf 'ROS_DISTRO=%s\n' "${ROS_DISTRO:-UNSET}"; command -v roscore || true; command -v rosversion || true; test -d /opt/ros/noetic && echo NOETIC_DIR_PRESENT || echo NOETIC_DIR_ABSENT; dpkg-query -W ros-noetic-ros-base 2>/dev/null || true; echo '=== conda ==='; command -v conda || true; echo '=== project contamination clues ==='; find "$HOME" -maxdepth 2 -type d \( -name '*am-planner*' -o -name '*Polynomial_DiT*' -o -name '*catkin*' \) 2>/dev/null | head -50
'@
        $encodedProbe = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($probe))
        Invoke-RecordedCommand -Name ('distro_' + ($distro -replace '[^A-Za-z0-9]+','_')) -FileName 'wsl.exe' -Arguments @('-d',$distro,'--','bash','--noprofile','--norc','-lc',("echo " + $encodedProbe + " | base64 -d | bash")) -Timeout 60 | Out-Null
    } else {
        [ordered]@{name=('distro_' + ($distro -replace '[^A-Za-z0-9]+','_')); command=$null; started_utc=(Get-Date).ToUniversalTime().ToString('o'); ended_utc=(Get-Date).ToUniversalTime().ToString('o'); exit_code=$null; timed_out=$false; stdout=''; stderr='DISTRIBUTION_NOT_LISTED'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $OutputDir ('distro_' + ($distro -replace '[^A-Za-z0-9]+','_') + '.json')) -Encoding utf8
    }
}
