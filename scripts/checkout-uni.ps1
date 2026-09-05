# Sparse-checkout one university folder (+ shared) at a completion tag.
#
# On portable / restricted PCs use checkout-uni.cmd (not .ps1).
#
# Examples:
#   .\scripts\checkout-uni.cmd -Pick aru
#   .\scripts\checkout-uni.ps1 -Pick unit-02
#   .\scripts\checkout-uni.ps1 -Pick aru -StudyLevel foundation
#   .\scripts\checkout-uni.cmd -Pick aston -Version 1.0.0
#   .\scripts\checkout-uni.cmd -Pick bcu -Commit abc1234
#   .\scripts\checkout-uni.cmd -Pick aru -ListTags
#   .\scripts\checkout-uni.ps1 -Pick aston -Tag "uni/aston/v1.0.0"
#
# Run from a clone of this repo (or pass -RepoUrl to clone fresh).

param(
    [Parameter(Mandatory = $true)]
    [string]$Pick,

    [string[]]$StudyLevel = @("all"),

    [string]$Version = "",

    [string]$Tag = "",

    [string]$Commit = "",

    [string]$RepoUrl = "",

    [string]$TargetDir = "",

    [switch]$ListTags,

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot/Get-UniRegistry.ps1"

function Invoke-SparseCheckout {
    param(
        [string]$Root,
        [string]$UniversityName,
        [string]$Ref
    )
    Set-Location $Root
    git sparse-checkout init --cone
    git sparse-checkout set "shared" $UniversityName "PIPELINE.md" "RUN.md" "UNIVERSITIES_REGISTRY.md" "CONTRIBUTING.md"
    git switch --detach $Ref
    Write-Host "Detached at $Ref"
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
    $commits = Get-UniCommitsFromHistory -Entry $entry -StudyLevels $StudyLevel -RepoRoot $repoRoot
    Write-Host "Commits from git history (--grep=$($entry.Scope)):"
    if ($commits) {
        $commits | Select-Object -First 10 | ForEach-Object {
            Write-Host "  $($_.Sha.Substring(0,7)) $($_.Subject)"
        }
    } else {
        Write-Host "  (none)"
    }
    if ($entry.Tag) {
        Write-Host "Registry tag: $($entry.Tag)"
    }
    if ($entry.Commit) {
        Write-Host "Registry commit: $($entry.Commit)"
    }
    return
}

$resolvedRef = Resolve-CheckoutRef -Entry $entry -StudyLevels $StudyLevel -Version $Version -Tag $Tag -Commit $Commit -RepoRoot $repoRoot
$refKind = if ($resolvedRef -match '^[0-9a-f]{7,40}$') { "commit" } else { "tag" }
$university = $entry.Folder

$uniDir = Join-Path $repoRoot $university
if (-not (Test-Path -LiteralPath $uniDir)) {
    throw "University folder not found: $uniDir"
}

Write-Host "University: $university"
Write-Host "Pick:       $Pick ($($entry.Scope))"
Write-Host "Ref:        $resolvedRef ($refKind)"
Write-Host ""

if ($DryRun) {
    Write-Host "Dry run - would run:"
    if ($RepoUrl) {
        if (-not $TargetDir) {
            $TargetDir = Join-Path (Get-Location) "UK_Uni_Data"
        }
        Write-Host "  git clone --filter=blob:none --sparse $RepoUrl $TargetDir"
        Write-Host "  cd $TargetDir"
    } else {
        Write-Host "  cd $repoRoot"
    }
    Write-Host "  git sparse-checkout init --cone"
    Write-Host "  git sparse-checkout set shared $university PIPELINE.md RUN.md UNIVERSITIES_REGISTRY.md CONTRIBUTING.md"
    Write-Host "  git switch --detach $resolvedRef"
    $subject = git -C $repoRoot show -s --format=%s $resolvedRef 2>$null
    if ($subject) {
        Write-Host ""
        Write-Host "Commit message: $subject"
    }
    return
}

if ($RepoUrl) {
    if (-not $TargetDir) {
        $TargetDir = Join-Path (Get-Location) "UK_Uni_Data"
    }
    git clone --filter=blob:none --sparse $RepoUrl $TargetDir
    Invoke-SparseCheckout -Root $TargetDir -UniversityName $university -Ref $resolvedRef
    return
}

Invoke-SparseCheckout -Root $repoRoot -UniversityName $university -Ref $resolvedRef
