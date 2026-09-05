# Restore one university folder from a tag or commit (default), or sparse-clone into a new folder.
#
# On portable / restricted PCs use checkout-uni.cmd (not .ps1).
#
# Default (safe): stay on your current branch; only replace that university's folder.
#   .\scripts\checkout-uni.cmd -Pick bcu -Commit af92caa
#   .\scripts\checkout-uni.cmd -Pick bcu -Commit af92caa -DryRun
#
# Sparse (destructive in an existing full clone): hides other universities - use only with -RepoUrl.
#   .\scripts\checkout-uni.cmd -Pick bcu -Commit af92caa -Sparse -RepoUrl https://github.com/... -TargetDir D:\bcu-only

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

    [switch]$DryRun,

    [switch]$Sparse,

    [switch]$IncludeShared
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
    $sparsePaths = @("shared", $UniversityName, "RUN.md", "UNIVERSITIES_REGISTRY.md", "CONTRIBUTING.md")
    if (Test-Path -LiteralPath (Join-Path $Root "PIPELINE.md")) {
        $sparsePaths += "PIPELINE.md"
    }
    git sparse-checkout set @sparsePaths
    git switch --detach $Ref
    Write-Host "Detached at $Ref"
    Write-Host "Sparse paths: $($sparsePaths -join ', ')"
}

function Invoke-RestoreUniversity {
    param(
        [string]$Root,
        [string]$UniversityName,
        [string]$Ref,
        [bool]$WithShared
    )
    Push-Location $Root
    try {
        $branch = git branch --show-current 2>$null
        if (-not $branch) {
            throw @"
Detached HEAD detected. Switch back to main before restoring a university folder:
  git sparse-checkout disable
  git switch main
Then re-run checkout-uni (without -Sparse).
"@
        }

        $paths = @($UniversityName)
        if ($WithShared) {
            $paths += "shared"
        }

        git restore --source $Ref -- @paths
        if ($LASTEXITCODE -ne 0) {
            git checkout $Ref -- @paths
        }

        Write-Host "Restored from $Ref onto branch ${branch}:"
        foreach ($path in $paths) {
            Write-Host "  $path/"
        }
        Write-Host "Other university folders were not changed."
    } finally {
        Pop-Location
    }
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
$useSparse = [bool]$Sparse -or [bool]$RepoUrl

if ($Sparse -and -not $RepoUrl) {
    Write-Warning "Sparse mode in an existing full clone hides other universities. Prefer default restore (omit -Sparse)."
}

Write-Host "University: $university"
Write-Host "Pick:       $Pick ($($entry.Scope))"
Write-Host "Ref:        $resolvedRef ($refKind)"
Write-Host "Mode:       $(if ($useSparse) { 'sparse' } else { 'restore folder only' })"
Write-Host ""

if ($DryRun) {
    Write-Host "Dry run - would run:"
    if ($useSparse) {
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
        Write-Host "  git sparse-checkout set shared $university RUN.md UNIVERSITIES_REGISTRY.md CONTRIBUTING.md"
        Write-Host "  git switch --detach $resolvedRef"
    } else {
        Write-Host "  cd $repoRoot"
        Write-Host "  git restore --source $resolvedRef -- $university"
        if ($IncludeShared) {
            Write-Host "  git restore --source $resolvedRef -- shared"
        }
        Write-Host "  (stay on current branch; other universities unchanged)"
    }
    $subject = git -C $repoRoot show -s --format=%s $resolvedRef 2>$null
    if ($subject) {
        Write-Host ""
        Write-Host "Commit message: $subject"
    }
    return
}

if ($useSparse) {
    if ($RepoUrl) {
        if (-not $TargetDir) {
            $TargetDir = Join-Path (Get-Location) "UK_Uni_Data"
        }
        git clone --filter=blob:none --sparse $RepoUrl $TargetDir
        Invoke-SparseCheckout -Root $TargetDir -UniversityName $university -Ref $resolvedRef
        return
    }
    Invoke-SparseCheckout -Root $repoRoot -UniversityName $university -Ref $resolvedRef
    return
}

Invoke-RestoreUniversity -Root $repoRoot -UniversityName $university -Ref $resolvedRef -WithShared:$IncludeShared
