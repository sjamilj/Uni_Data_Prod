# Start Microsoft Edge with CDP on port 9222 for LSBU course download.
# From repo root:
#   powershell -ExecutionPolicy Bypass -File "London South Bank University\code\start-edge-cdp.ps1"

$ErrorActionPreference = "Stop"

$edgeCandidates = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
)

$edge = $edgeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) {
    Write-Error "msedge.exe not found. Install Microsoft Edge or edit this script."
}

$profile = Join-Path $PSScriptRoot ".cdp-edge-profile"
New-Item -ItemType Directory -Force -Path $profile | Out-Null

$running = Get-Process -Name msedge -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "Stopping $($running.Count) existing Edge process(es) so CDP can bind to port 9222..."
    $running | Stop-Process -Force
    Start-Sleep -Seconds 2
}

$warmupUrl = "https://www.lsbu.ac.uk/study/course-finder/msc-cyber-security"
Write-Host "Starting Edge (dedicated CDP profile: $profile)"
Write-Host "Pass Cloudflare on the course page, then run presetup (leave this window open)."

Start-Process -FilePath $edge -ArgumentList @(
    "--remote-debugging-port=9222",
    "--remote-debugging-address=127.0.0.1",
    "--user-data-dir=$profile",
    "--remote-allow-origins=*",
    "--no-first-run",
    "--no-default-browser-check",
    $warmupUrl
)

$ok = $false
foreach ($wait in 3, 5, 7) {
    Start-Sleep -Seconds $wait
    try {
        $ver = Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version" -TimeoutSec 5
        Write-Host "CDP OK: $($ver.Browser)"
        $ok = $true
        break
    } catch {
        Write-Host "Waiting for CDP on :9222 (${wait}s)..."
    }
}

if (-not $ok) {
    Write-Host ""
    Write-Host "CDP still not reachable. Check:"
    Write-Host "  netstat -ano | findstr :9222"
    Write-Host "  Get-Process msedge"
    Write-Host "Re-run this script after closing all Edge windows."
    exit 1
}
