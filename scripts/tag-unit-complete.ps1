# Tag a university as pipeline-complete (dev_courses CSV required).
# Usage:
#   .\scripts\tag-unit-complete.ps1 -University "Aston University" -Unit unit-02 -Slug aston
#   .\scripts\tag-unit-complete.ps1 -University "Aston University" -Unit unit-02 -Slug aston -Version 1.0.1

param(
    [Parameter(Mandatory = $true)]
    [string]$University,

    [Parameter(Mandatory = $true)]
    [string]$Unit,

    [Parameter(Mandatory = $true)]
    [string]$Slug,

    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if ($Unit -notmatch '^unit-\d{2}$') {
    throw "Unit must look like unit-03 (got '$Unit')"
}
if ($Slug -notmatch '^[a-z0-9-]+$') {
    throw "Slug must be lowercase letters, digits, or hyphens (got '$Slug')"
}

$uniDir = Join-Path $repoRoot $University
if (-not (Test-Path -LiteralPath $uniDir)) {
    throw "University folder not found: $uniDir"
}

$csv = Get-ChildItem -LiteralPath (Join-Path $uniDir "output") -Filter "dev_courses_*.csv" -ErrorAction SilentlyContinue
if (-not $csv) {
    throw "No output/dev_courses_*.csv under '$University'. Do not tag until Phase 5 export exists."
}

$unitTag = $Unit
$uniTag = "uni/$Slug/v$Version"

$existingUnit = git tag -l $unitTag
if ($existingUnit) {
    throw "Tag already exists: $unitTag"
}
$existingUni = git tag -l $uniTag
if ($existingUni) {
    throw "Tag already exists: $uniTag"
}

$sha = (git rev-parse HEAD).Trim()
$courseCount = 0
try {
    $courseCount = (Import-Csv -LiteralPath $csv[0].FullName).Count
} catch {
    $courseCount = 0
}

git tag -a $unitTag -m "${Unit}: $University pipeline complete"
git tag -a $uniTag -m "${University}: dev_courses CSV exported ($courseCount courses)"

Write-Host "Created tags:"
Write-Host "  $unitTag"
Write-Host "  $uniTag"
Write-Host "Commit: $sha"
Write-Host "CSV: $($csv[0].Name) ($courseCount rows)"
Write-Host ""
Write-Host "Paste into UNIVERSITIES_REGISTRY.md:"
Write-Host "| $Unit | $Slug | $University | complete | $uniTag | $sha |"
Write-Host ""
Write-Host "Push when ready:"
Write-Host "  git push origin $unitTag $uniTag"
