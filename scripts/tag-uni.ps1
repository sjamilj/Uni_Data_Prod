# Tag a university snapshot. Versions live in tags only (v1.0.0, v1.0.1, ...).
#
# Examples:
#   .\scripts\tag-uni.ps1 -Pick aston
#   .\scripts\tag-uni.ps1 -Pick unit-02 -StudyLevel foundation
#   .\scripts\tag-uni.ps1 -Pick aru -StudyLevel foundation,undergraduate,postgraduate -Version 1.0.1
#   .\scripts\tag-uni.ps1 -Pick bcu -BumpPatch
#   .\scripts\tag-uni.ps1 -Pick aston -ListTags

param(
    [string]$Pick = "",

    [string[]]$StudyLevel = @("all"),

    [string]$Version = "",

    [switch]$BumpPatch,

    [switch]$ListTags,

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot/Get-UniRegistry.ps1"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if ($ListTags) {
    if (-not $Pick) {
        git tag -l "uni/*" | Sort-Object
        return
    }
    $entry = Resolve-UniEntry -Pick $Pick -RepoRoot $repoRoot
    git tag -l "uni/$($entry.Slug)/*" | Sort-Object
    return
}

if (-not $Pick) {
    throw "Pick is required unless -ListTags is used."
}

$entry = Resolve-UniEntry -Pick $Pick -RepoRoot $repoRoot
$label = Get-StudyLevelLabel -StudyLevels $StudyLevel

if ($BumpPatch) {
    $Version = Get-LatestUniTagVersion -Slug $entry.Slug -StudyLevels $StudyLevel -RepoRoot $repoRoot
} elseif (-not $Version) {
    $Version = "1.0.0"
}

$tagName = Get-UniTagName -Slug $entry.Slug -Version $Version -StudyLevels $StudyLevel
$unitTag = $entry.Unit

if ($label -eq "all") {
    $existingUnit = git tag -l $unitTag
    if ($existingUnit) {
        throw "Unit tag already exists: $unitTag. Use -StudyLevel for partial work, or delete/move the old tag."
    }
}

$existing = git tag -l $tagName
if ($existing) {
    throw "Tag already exists: $tagName"
}

if ($label -eq "all") {
    $csv = Get-ChildItem -LiteralPath (Join-Path $repoRoot $entry.Folder "output") -Filter "dev_courses_*.csv" -ErrorAction SilentlyContinue
    if (-not $csv) {
        throw "No output/dev_courses_*.csv under '$($entry.Folder)'. Tag only after export exists."
    }
}

$sha = (git rev-parse HEAD).Trim()
$tagMessage = if ($label -eq "all") {
    "$($entry.Unit): $($entry.Folder) pipeline complete"
} else {
    "$($entry.Unit): $($entry.Folder) $label pipeline complete"
}

Write-Host "University: $($entry.Folder)"
Write-Host "Scope:      $($entry.Scope)"
Write-Host "Levels:     $label"
Write-Host "Version:    v$($Version.TrimStart('v'))"
Write-Host "Tag:        $tagName"
Write-Host "Commit:     $sha"
Write-Host ""

if ($DryRun) {
    Write-Host "Dry run only. No git tag created."
    return
}

git tag -a $tagName -m $tagMessage

if ($label -eq "all") {
    git tag -a $unitTag -m $tagMessage
    Write-Host "Created tags:"
    Write-Host "  $tagName"
    Write-Host "  $unitTag"
} else {
    Write-Host "Created tag:"
    Write-Host "  $tagName"
}

Write-Host ""
Write-Host "Registry row (update UNIVERSITIES_REGISTRY.md tag + commit columns):"
Write-Host "| $($entry.Unit) | $($entry.Slug) | $($entry.Folder) | complete | $tagName | $sha |"
Write-Host ""
Write-Host "Check out later:"
Write-Host "  .\scripts\checkout-uni.ps1 -University `"$($entry.Folder)`" -Tag `"$tagName`""
Write-Host ""
Write-Host "Push when ready:"
if ($label -eq "all") {
    Write-Host "  git push origin $tagName $unitTag"
} else {
    Write-Host "  git push origin $tagName"
}
