# Phase 2: download + clean course pages for every university, one by one.
# Aston, ARU, and Birmingham City University are skipped by default (already done).
#
# Resume after power cut / crash:
#   .\run_all_download_clean.ps1 -Resume
# Per-university URL downloads also resume from output/scrape_progress.json.
#
# Examples:
#   .\run_all_download_clean.ps1 -Resume
#   .\run_all_download_clean.ps1 -Resume -University "Keele University"
#   .\run_all_download_clean.ps1 -CleanOnly -Resume
#   .\run_all_download_clean.ps1 -DryRun

[CmdletBinding()]
param(
    [switch]$Resume,
    [switch]$Fresh,
    [switch]$CleanOnly,
    [switch]$DownloadOnly,
    [int]$Limit = 0,
    [string[]]$University = @(),
    [string[]]$SkipUniversities = @(),
    [switch]$IncludeDone,
    [switch]$FailFast,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
$Runner = Join-Path $RepoRoot "shared\run_all_download_clean.py"

if (-not (Test-Path $Runner)) {
    throw "Missing script: $Runner"
}
if ($Resume -and $Fresh) {
    throw "-Resume and -Fresh cannot be used together."
}
if ($CleanOnly -and $DownloadOnly) {
    throw "-CleanOnly and -DownloadOnly cannot be used together."
}

$pyArgs = @($Runner)
if ($Resume) { $pyArgs += "--resume" }
if ($Fresh) { $pyArgs += "--fresh" }
if ($CleanOnly) { $pyArgs += "--clean-only" }
if ($DownloadOnly) { $pyArgs += "--download-only" }
if ($Limit -gt 0) { $pyArgs += @("--limit", "$Limit") }
foreach ($name in $University) {
    if ($name) { $pyArgs += @("--university", $name) }
}
foreach ($name in $SkipUniversities) {
    if ($name) { $pyArgs += @("--skip", $name) }
}
if ($IncludeDone) { $pyArgs += "--include-done" }
if ($FailFast) { $pyArgs += "--fail-fast" }
if ($DryRun) { $pyArgs += "--dry-run" }

Write-Host "python $($pyArgs -join ' ')"
& python @pyArgs
if ($LASTEXITCODE -ne 0) {
    throw "Batch download/clean failed: exit code $LASTEXITCODE"
}
