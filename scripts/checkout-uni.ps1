# Sparse-checkout one university folder (+ shared) at a completion tag.
# Usage:
#   .\scripts\checkout-uni.ps1 -University "Aston University" -Tag "uni/aston/v1.0.0"
# Run from a clone of this repo (or pass -RepoUrl to clone fresh).

param(
    [Parameter(Mandatory = $true)]
    [string]$University,

    [Parameter(Mandatory = $true)]
    [string]$Tag,

    [string]$RepoUrl = "",
    [string]$TargetDir = ""
)

$ErrorActionPreference = "Stop"

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

if ($RepoUrl) {
    if (-not $TargetDir) {
        $TargetDir = Join-Path (Get-Location) "UK_Uni_Data"
    }
    git clone --filter=blob:none --sparse $RepoUrl $TargetDir
    Invoke-SparseCheckout -Root $TargetDir -UniversityName $University -TagName $Tag
    return
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$uniDir = Join-Path $repoRoot $University
if (-not (Test-Path -LiteralPath $uniDir)) {
    throw "University folder not found: $uniDir"
}

$tagExists = git -C $repoRoot tag -l $Tag
if (-not $tagExists) {
    throw "Tag not found: $Tag"
}

Invoke-SparseCheckout -Root $repoRoot -UniversityName $University -TagName $Tag
