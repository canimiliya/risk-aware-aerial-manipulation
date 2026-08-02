param(
    [string]$Manifest = "docs/evidence/S1-R1/gpu_dependency_recovery/official_wheel_manifest.json",
    [string]$Wheelhouse = "D:\WSL\downloads\torch-2.7.1-cu128-py39-runtime",
    [int]$MaxAttempts = 5
)

$ErrorActionPreference = "Stop"
$root = (Get-Location).Path
$manifestPath = Join-Path $root $Manifest
if (-not (Test-Path -LiteralPath $manifestPath)) { throw "manifest missing: $manifestPath" }
$data = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
$allowed = @("download.pytorch.org", "download-r2.pytorch.org", "pypi.org", "files.pythonhosted.org")
New-Item -ItemType Directory -Force -Path $Wheelhouse | Out-Null
$logPath = Join-Path $Wheelhouse "download_log.jsonl"

function Get-Hash([string]$Path) {
    (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Test-Complete($row, [string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    $item = Get-Item -LiteralPath $Path
    return ($item.Length -eq [int64]$row.size -and (Get-Hash $Path) -eq $row.sha256.ToLowerInvariant())
}

foreach ($row in $data.rows) {
    $urlHost = ([Uri]$row.url).Host
    if ($allowed -notcontains $urlHost) { throw "disallowed URL host: $urlHost" }
    $target = Join-Path $Wheelhouse $row.filename
    $part = "$target.part"
    $record = [ordered]@{ name=$row.name; version=$row.version; url=$row.url; target=$target; started=(Get-Date).ToUniversalTime().ToString("o"); attempts=0; status="STARTED" }
    if (Test-Complete $row $target) { $record.status="ALREADY_VALID"; ($record | ConvertTo-Json -Compress) | Add-Content -LiteralPath $logPath; continue }
    if (Test-Path -LiteralPath $target) {
        $quarantine = "$target.invalid.$([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))"
        Move-Item -LiteralPath $target -Destination $quarantine
        $record.quarantined = $quarantine
    }
    for ($attempt=1; $attempt -le $MaxAttempts; $attempt++) {
        $record.attempts = $attempt
        & curl.exe --silent --show-error -L --fail --retry 10 --retry-all-errors --retry-delay 10 --connect-timeout 30 --speed-time 120 --speed-limit 1024 -C - $row.url -o $part 2>&1 | Out-File -Append -Encoding utf8 -FilePath (Join-Path $Wheelhouse "curl.log")
        if (Test-Complete $row $part) {
            Move-Item -LiteralPath $part -Destination $target
            $record.status = "DOWNLOADED_AND_VERIFIED"
            break
        }
        $record.last_part_bytes = if (Test-Path -LiteralPath $part) { (Get-Item -LiteralPath $part).Length } else { 0 }
        Start-Sleep -Seconds ([int]([math]::Pow(2, $attempt) * 10))
    }
    if ($record.status -ne "DOWNLOADED_AND_VERIFIED") { $record.status="FAILED_PARTIAL_PRESERVED"; ($record | ConvertTo-Json -Compress) | Add-Content -LiteralPath $logPath; throw "download failed for $($row.filename); partial preserved at $part" }
    ($record | ConvertTo-Json -Compress) | Add-Content -LiteralPath $logPath
}
Write-Output "All manifest wheels are present and verified in $Wheelhouse"
