# Phase 1: scrape course URLs -> output/course_urls.csv
#
# Examples:
#   .\run_scrape_urls.ps1 -University "Anglia Ruskin University - ARU"
#   .\run_scrape_urls.ps1 -University "Anglia Ruskin University - ARU" -Fresh
#   .\run_scrape_urls.ps1 -University "Anglia Ruskin University - ARU" -AppendUrls

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$University,

    [switch]$Fresh,
    [switch]$AppendUrls
)

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$CodeDir = Join-Path (Join-Path $RepoRoot $University) "code"
$ScrapeScript = Join-Path $RepoRoot "shared\scrape_course_urls.py"

if (-not (Test-Path $CodeDir)) {
    throw "University code folder not found: $CodeDir"
}
if (-not (Test-Path $ScrapeScript)) {
    throw "Missing script: $ScrapeScript"
}

$scrapeArgs = @($ScrapeScript, "--code-dir", $CodeDir)
if ($Fresh) { $scrapeArgs += "--fresh" }
if ($AppendUrls) { $scrapeArgs += "--append-urls" }

Write-Host "University : $University"
Write-Host "Code dir   : $CodeDir"
Write-Host "python $($scrapeArgs -join ' ')"
& python @scrapeArgs
if ($LASTEXITCODE -ne 0) {
    throw "Scrape failed: exit code $LASTEXITCODE"
}
