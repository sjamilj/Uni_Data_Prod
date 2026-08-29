# Phase 2a: clean uni_req HTML -> output/clean/uni/*.md
#
# Examples:
#   .\run_uni_clean.ps1 -University "Anglia Ruskin University - ARU"

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$University
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

$args = @($DownloadScript, "--code-dir", $CodeDir, "--clean-uni-only")

Write-Host "University : $University"
Write-Host "Code dir   : $CodeDir"
Write-Host "python $($args -join ' ')"
& python @args
if ($LASTEXITCODE -ne 0) {
    throw "Uni clean failed: exit code $LASTEXITCODE"
}
