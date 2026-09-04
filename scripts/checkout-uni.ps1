# Sparse-checkout one university folder (+ shared) at a completion tag.
#
# Examples:
#   .\scripts\checkout-uni.ps1 -Pick aru
#   .\scripts\checkout-uni.ps1 -Pick unit-02
#   .\scripts\checkout-uni.ps1 -Pick aru -StudyLevel foundation
#   .\scripts\checkout-uni.ps1 -Pick aston -Version 1.0.0
#   .\scripts\checkout-uni.ps1 -Pick aru -ListTags
#   .\scripts\checkout-uni.ps1 -Pick aston -Tag "uni/aston/v1.0.0"
#
# Run from a clone of this repo (or pass -RepoUrl to clone fresh).

param(
    [Parameter(Mandatory = $true)]
    [string]$Pick,

    [string[]]$StudyLevel = @("all"),

    [string]$Version = "",

    [string]$Tag = "",

    [string]$RepoUrl = "",

    [string]$TargetDir = "",

    [switch]$ListTags
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot/Get-UniRegistry.ps1"

function Invoke-SparseCheckout {
    param(
        [string]$Root,
        [string]$UniversityName,
        [string]$TagName
    )
    Set-Location $Root
    git sparse-checkout init --cone
    git sparse-checkout set "shared" $UniversityName "PIPELINE.md" "RUN.md" "UNIVERSITIES_REGISTRY.md" "CONTRIBUTING.md"
    git switch --detach $TagName
    Write-Host "Detached at $TagName"
    Write-Host "Sparse paths: shared, $UniversityName, pipeline docs"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$entry = Resolve-UniEntry -Pick $Pick -RepoRoot $repoRoot

if ($ListTags) {
    $tags = Get-UniTags -Slug $entry.Slug -Unit $entry.Unit -RepoRoot $repoRoot
    Write-Host "Tags for $($entry.Folder) ($($entry.Unit) / $($entry.Slug)):"
    if ($tags) {
        $tags | ForEach-Object { Write-Host "  $_" }
    } else {
        Write-Host "  (none)"
    }
    if ($entry.Tag) {
        Write-Host "Registry tag: $($entry.Tag)"
    }
    return
}

$resolvedTag = Resolve-CheckoutTag -Entry $entry -StudyLevels $StudyLevel -Version $Version -Tag $Tag -RepoRoot $repoRoot
$university = $entry.Folder

$uniDir = Join-Path $repoRoot $university
if (-not (Test-Path -LiteralPath $uniDir)) {
    throw "University folder not found: $uniDir"
}

Write-Host "University: $university"
Write-Host "Pick:       $Pick ($($entry.Scope))"
Write-Host "Tag:        $resolvedTag"
Write-Host ""

if ($RepoUrl) {
    if (-not $TargetDir) {
        $TargetDir = Join-Path (Get-Location) "UK_Uni_Data"
    }
    git clone --filter=blob:none --sparse $RepoUrl $TargetDir
    Invoke-SparseCheckout -Root $TargetDir -UniversityName $university -TagName $resolvedTag
    return
}

Invoke-SparseCheckout -Root $repoRoot -UniversityName $university -TagName $resolvedTag
