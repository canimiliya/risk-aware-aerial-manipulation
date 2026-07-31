$ErrorActionPreference = 'Stop'
$downloadRoot = Join-Path $env:USERPROFILE 'Downloads\s1-r1-gpu-deps'
New-Item -ItemType Directory -Force $downloadRoot | Out-Null
$items = @(
  @{ Name='nvidia_cublas_cu12-12.8.3.14-py3-none-manylinux_2_27_x86_64.whl'; Url='https://files.pythonhosted.org/packages/82/df/4b01f10069e23c641f116c62fc31e31e8dc361a153175d81561d15c8143b/nvidia_cublas_cu12-12.8.3.14-py3-none-manylinux_2_27_x86_64.whl'; Size=609620630 },
  @{ Name='nvidia_cudnn_cu12-9.7.1.26-py3-none-manylinux_2_27_x86_64.whl'; Url='https://files.pythonhosted.org/packages/25/dc/dc825c4b1c83b538e207e34f48f86063c88deaa35d46c651c7c181364ba2/nvidia_cudnn_cu12-9.7.1.26-py3-none-manylinux_2_27_x86_64.whl'; Size=726851421 }
)
$chunk = 32MB
foreach ($item in $items) {
  $final = Join-Path $downloadRoot $item.Name
  if ((Test-Path $final) -and ((Get-Item $final).Length -eq $item.Size)) { continue }
  $parts = @()
  $jobs = @()
  for ($start = 0; $start -lt $item.Size; $start += $chunk) {
    $end = [Math]::Min($item.Size - 1, $start + $chunk - 1)
    $part = Join-Path $downloadRoot ("{0}.{1:D4}" -f $item.Name, [int]($start / $chunk))
    $parts += $part
    $jobs += Start-Process -FilePath 'curl.exe' -WindowStyle Hidden -PassThru -ArgumentList @('-L','--fail','--retry','2','--connect-timeout','30','--max-time','900','--range',"$start-$end",$item.Url,'-o',$part)
  }
  $jobs | Wait-Process
  if (@($jobs | Where-Object ExitCode -ne 0).Count -gt 0) { throw "chunk download failed: $($item.Name)" }
  $stream = [System.IO.File]::Open($final, [System.IO.FileMode]::Create)
  try { foreach ($part in $parts) { $bytes = [System.IO.File]::ReadAllBytes($part); $stream.Write($bytes, 0, $bytes.Length) } } finally { $stream.Dispose() }
  foreach ($part in $parts) { Remove-Item -LiteralPath $part -Force }
}
Get-ChildItem $downloadRoot -File | Get-FileHash -Algorithm SHA256 | Format-Table -AutoSize
