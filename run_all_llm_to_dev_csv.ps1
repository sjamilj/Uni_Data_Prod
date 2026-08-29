# Run phases 3-5 (LLM -> normalize -> dev CSV) for every university with clean/courses/*.md.
#
# Examples:
#   .\run_all_llm_to_dev_csv.ps1 -Resume
#   .\run_all_llm_to_dev_csv.ps1 -Resume -SkipUniversities "University of Essex"
#   .\run_all_llm_to_dev_csv.ps1 -Resume -OnlyUniversities "Aston University"

[CmdletBinding()]
param(
    [switch]$Resume,
    [string[]]$SkipUniversities = @(),
    [string[]]$OnlyUniversities = @(),
    [int]$Limit = 0
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
$Runner = Join-Path $RepoRoot "run_llm_to_dev_csv.ps1"

if (-not (Test-Path $Runner)) {
    throw "Missing script: $Runner"
}

$skip = @{}
foreach ($name in $SkipUniversities) {
    if ($name) { $skip[$name.Trim()] = $true }
}

$universities = Get-ChildItem $RepoRoot -Directory | Where-Object {
    $_.Name -notin @("shared", "dashboard", "_university_template") -and
    -not $_.Name.StartsWith(".") -and
    (Test-Path (Join-Path $_.FullName "code\ENV.MD"))
}

if ($OnlyUniversities.Count -gt 0) {
    $only = @{}
    foreach ($name in $OnlyUniversities) {
        if ($name) { $only[$name.Trim()] = $true }
    }
    $universities = $universities | Where-Object { $only.ContainsKey($_.Name) }
}

$targets = @()
foreach ($uni in $universities) {
    if ($skip.ContainsKey($uni.Name)) { continue }
    $coursesDir = Join-Path $uni.FullName "output\clean\courses"
    $mdCount = 0
    if (Test-Path $coursesDir) {
        $mdCount = @(Get-ChildItem $coursesDir -Filter "*.md" -File).Count
    }
    if ($mdCount -eq 0) {
        Write-Host "SKIP (no clean/courses): $($uni.Name)" -ForegroundColor Yellow
        continue
    }
    $targets += [pscustomobject]@{
        Name = $uni.Name
        Courses = $mdCount
    }
}

if ($targets.Count -eq 0) {
    Write-Host "No universities with clean/courses markdown found."
    return
}

Write-Host "Universities to process: $($targets.Count)" -ForegroundColor Cyan
$targets | Format-Table -AutoSize

$failed = @()
$index = 0
foreach ($target in $targets) {
    $index++
    Write-Host ""
    Write-Host ("=" * 72) -ForegroundColor DarkGray
    Write-Host "[$index/$($targets.Count)] $($target.Name) ($($target.Courses) courses)" -ForegroundColor Cyan

    $args = @("-University", $target.Name)
    if ($Resume) { $args += "-Resume" }
    if ($Limit -gt 0) { $args += @("-Limit", $Limit) }

    try {
        & $Runner @args
    }
    catch {
        Write-Host "FAILED: $($target.Name) - $_" -ForegroundColor Red
        $failed += $target.Name
    }
}

Write-Host ""
if ($failed.Count -eq 0) {
    Write-Host "All universities completed." -ForegroundColor Green
}
else {
    Write-Host "Failed universities:" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host "  $_" }
    exit 1
}
