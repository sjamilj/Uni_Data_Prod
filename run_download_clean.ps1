# Phase 2b: download course HTML + clean to markdown (no URL scrape)
#
# Resume after power cut: re-run with -Resume (default).
#
# Examples:
#   .\run_download_clean.ps1 -University "Anglia Ruskin University - ARU"
#   .\run_download_clean.ps1 -University "Anglia Ruskin University - ARU" -Resume
#   .\run_download_clean.ps1 -University "Anglia Ruskin University - ARU" -Fresh
#   .\run_download_clean.ps1 -University "Anglia Ruskin University - ARU" -Limit 5

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$University,

    [switch]$Resume,
    [switch]$Fresh,
    [int]$Limit = 0
)

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$CodeDir = Join-Path (Join-Path $RepoRoot $University) "code"
$DownloadScript = Join-Path $RepoRoot "shared\download_and_clean_course_pages.py"

if (-not (Test-Path $CodeDir)) {
    throw "University code folder not found: $CodeDir"
}
if (-not (Test-Path $DownloadScript)) {
    throw "Missing script: $DownloadScript"
}
if ($Resume -and $Fresh) {
    throw "-Resume and -Fresh cannot be used together."
}

$downloadArgs = @($DownloadScript, "--code-dir", $CodeDir)
if ($Fresh) {
    $downloadArgs += "--fresh"
}
if ($Limit -gt 0) {
    $downloadArgs += @("--limit", $Limit)
}

Write-Host "University : $University"
Write-Host "Code dir   : $CodeDir"
if ($Resume) {
    Write-Host "Mode       : RESUME (skips downloaded URLs in scrape_progress.json)" -ForegroundColor Green
}
if ($Fresh) {
    Write-Host "Mode       : FRESH (re-download all course URLs)" -ForegroundColor Yellow
}

Write-Host "python $($downloadArgs -join ' ')"
& python @downloadArgs
if ($LASTEXITCODE -ne 0) {
    throw "Download/clean failed: exit code $LASTEXITCODE"
}
