# Print git add + git commit commands. Does not run git.
#
# Auto-detect files from git status (omit -Paths), or pass paths manually.
#
# Examples:
#   .\scripts\commit-uni.ps1 -Pick aru -Type feat -StudyLevel foundation
#   .\scripts\commit-uni.ps1 -Pick aru -Type feat -StudyLevel postgraduate -IncludeShared
#   .\scripts\commit-uni.ps1 -Pick aru -Type feat -StudyLevel foundation -Paths "code/.env,readme.md"
#   .\scripts\commit-uni.ps1 -Pick infra -Type chore -Summary "add commit and tag helper scripts"
#   .\scripts\commit-uni.ps1 -Pick infra -Type docs

param(
    [Parameter(Mandatory = $true)]
    [string]$Pick,

    [string[]]$Paths = @(),

    [ValidateSet("feat", "fix", "wip", "chore", "docs")]
    [string]$Type = "feat",

    [string[]]$StudyLevel = @("all"),

    [string]$Summary = "",

    [Alias("WithShared")]
    [switch]$IncludeShared
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot/Get-UniRegistry.ps1"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$infraPicks = @("infra", "repo", "chore", "docs")
$isInfra = $infraPicks -contains $Pick.Trim().ToLower()

function Get-GitStatusPaths {
    param(
        [string]$Root,
        [string[]]$PathSpecs = @()
    )

    Push-Location $Root
    try {
        if ($PathSpecs.Count -gt 0) {
            $lines = git status --porcelain -- @PathSpecs
        } else {
            $lines = git status --porcelain
        }
    } finally {
        Pop-Location
    }

    $result = @()
    foreach ($line in @($lines)) {
        if (-not $line -or $line.Length -lt 4) { continue }

        $path = $line.Substring(3).Trim()
        if ($path -match ' -> ') {
            $path = ($path -split ' -> ', 2)[-1].Trim()
        }
        $path = $path.Trim('"').Replace('\', '/')
        if ($path) {
            $result += $path
        }
    }

    return $result | Select-Object -Unique
}

function Resolve-CommitPath {
    param(
        [string]$RawPath,
        [string]$UniFolder,
        [string]$Root
    )

    $path = $RawPath.Trim().Trim('"', "'").Replace('/', '\')
    if (-not $path) {
        throw "Empty file path."
    }

    if ([System.IO.Path]::IsPathRooted($path)) {
        $full = [System.IO.Path]::GetFullPath($path)
    } elseif ($path.StartsWith("$UniFolder\") -or $path -eq $UniFolder) {
        $full = [System.IO.Path]::GetFullPath((Join-Path $Root $path))
    } elseif ($path.StartsWith("shared\") -or $path -eq "shared") {
        $full = [System.IO.Path]::GetFullPath((Join-Path $Root $path))
    } else {
        $full = [System.IO.Path]::GetFullPath((Join-Path (Join-Path $Root $UniFolder) $path))
    }

    $rootNorm = [System.IO.Path]::GetFullPath($Root)
    if (-not $full.StartsWith($rootNorm, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path escapes repo root: $RawPath"
    }

    $relative = $full.Substring($rootNorm.Length).TrimStart('\', '/')
    return $relative.Replace('\', '/')
}

function Get-InfraStatusPaths {
    param([string]$Root)

    $registry = Get-UniRegistry -RepoRoot $Root
    $uniPrefixes = $registry | ForEach-Object { $_.Folder.Replace('\', '/') }
    $all = Get-GitStatusPaths -Root $Root

    return $all | Where-Object {
        $path = $_
        $underUni = $false
        foreach ($prefix in $uniPrefixes) {
            if ($path -eq $prefix -or $path.StartsWith("$prefix/")) {
                $underUni = $true
                break
            }
        }
        -not $underUni
    }
}

if ($isInfra) {
    $scope = "repo"
    $label = "repo infra"

    if ($Type -eq "docs") {
        if ($Summary.Trim()) {
            $message = "docs: $($Summary.Trim())"
        } else {
            $message = "docs: update project documentation"
        }
    } elseif ($Type -eq "chore" -or $Type -eq "fix" -or $Type -eq "wip") {
        if (-not $Summary.Trim()) {
            throw "Summary is required for $Type commits. Example: -Summary 'add commit and tag helper scripts'"
        }
        if ($Type -eq "chore") {
            $message = "chore: $($Summary.Trim())"
        } else {
            $message = "$Type($scope): $($Summary.Trim())"
        }
    } else {
        throw "Use -Type chore or -Type docs with -Pick infra."
    }

    if ($Paths.Count -gt 0) {
        $resolved = @()
        foreach ($raw in $Paths) {
            foreach ($part in ($raw -split ',')) {
                $token = $part.Trim().Trim('"', "'").Replace('\', '/')
                if ($token) { $resolved += $token }
            }
        }
        $resolved = $resolved | Select-Object -Unique
    } else {
        $resolved = Get-InfraStatusPaths -Root $repoRoot
    }
} else {
    $entry = Resolve-UniEntry -Pick $Pick -RepoRoot $repoRoot
    $scope = $entry.Scope
    $folder = $entry.Folder
    $label = $entry.Folder
    $slug = $entry.Slug

    $baseMessage = ""
    if ($Type -eq "fix" -or $Type -eq "wip") {
        if (-not $Summary.Trim()) {
            throw "Summary is required for $Type commits. Example: -Summary 'correct foundation URL patterns'"
        }
        $baseMessage = "$Type($scope): $($Summary.Trim())"
    } elseif ($Type -eq "chore" -or $Type -eq "docs") {
        if (-not $Summary.Trim()) {
            throw "Summary is required for $Type commits."
        }
        $baseMessage = "$Type($scope): $($Summary.Trim())"
    } else {
        $phrase = Format-StudyLevelCommitPhrase -StudyLevels $StudyLevel
        $baseMessage = "feat($scope): $phrase"
    }

    $version = Resolve-NextCommitVersion -Slug $slug -StudyLevels $StudyLevel -Type $Type -Scope $scope -RepoRoot $repoRoot
    $latestVersion = Get-LatestVersionFromHistory -Slug $slug -StudyLevels $StudyLevel -Scope $scope -RepoRoot $repoRoot
    $message = Format-VersionedCommitMessage -BaseMessage $baseMessage -Version $version

    if ($Paths.Count -gt 0) {
        $resolved = @()
        foreach ($raw in $Paths) {
            foreach ($part in ($raw -split ',')) {
                $token = $part.Trim().Trim('"', "'")
                if ($token) {
                    $resolved += Resolve-CommitPath -RawPath $token -UniFolder $folder -Root $repoRoot
                }
            }
        }
        $resolved = $resolved | Select-Object -Unique
    } else {
        $specs = @($folder)
        if ($IncludeShared) { $specs += "shared" }
        $resolved = Get-GitStatusPaths -Root $repoRoot -PathSpecs $specs
        if ($IncludeShared) {
            $resolved = $resolved | Where-Object {
                $_.StartsWith("$folder/") -or $_.StartsWith("shared/")
            }
        } else {
            $resolved = $resolved | Where-Object { $_.StartsWith("$folder/") }
        }
    }

    $foreign = $resolved | Where-Object {
        $isUni = $_.StartsWith("$folder/")
        $isShared = $IncludeShared -and $_.StartsWith("shared/")
        -not ($isUni -or $isShared)
    }
    if ($foreign) {
        throw "File(s) outside $($folder)$(if ($IncludeShared) { ' and shared/' } else { '' }):`n  $($foreign -join "`n  ")"
    }

    if (-not $IncludeShared -and $Paths.Count -eq 0) {
        $sharedPending = Get-GitStatusPaths -Root $repoRoot -PathSpecs @("shared") |
            Where-Object { $_.StartsWith("shared/") }
        if ($sharedPending) {
            $script:sharedHint = @(
                "# shared/ also has unstaged changes (not included):"
            ) + ($sharedPending | ForEach-Object { "#   $_" }) + @(
                "# add university + shared together:"
                "#   .\scripts\commit-uni.ps1 -Pick $Pick -Type $Type -StudyLevel $(Get-StudyLevelLabel -StudyLevels $StudyLevel) -IncludeShared"
            )
        }
    }
}

if (-not $resolved) {
    if ($isInfra) {
        throw @(
            "No unstaged files found for repo infra (scripts/, docs/, root markdown)."
            ""
            "Check: git status"
            "Or pass paths: -Paths scripts/commit-uni.ps1,CONTRIBUTING.md"
        ) -join "`n"
    }
    throw @(
        "No unstaged files under: $folder"
        ""
        "Check: git status -- `"$folder`""
        "output/ is gitignored - only tracked files appear here."
        "Or pass paths: -Paths code/.env,readme.md"
        "Or include shared/: -IncludeShared  (alias: -WithShared)"
    ) -join "`n"
}

$addCmd = "git add -- " + (($resolved | ForEach-Object { "`"$_`"" }) -join ' ')
$commitCmd = "git commit -m `"$message`""

Write-Host "# $label"
if (-not $isInfra) {
    $levelLabel = Get-StudyLevelLabel -StudyLevels $StudyLevel
    Write-Host "# scope: $scope | type: $Type | levels: $levelLabel | version: v$version"
    if ($latestVersion) {
        Write-Host "# history: latest v$latestVersion (tags + git log for $scope)"
    } else {
        Write-Host "# history: no prior version (starting v$version)"
    }
} else {
    Write-Host "# type: $Type"
}
Write-Host "# files from git status:"
foreach ($path in $resolved) {
    Write-Host "#   $path"
}
Write-Host ""
Write-Host $addCmd
Write-Host $commitCmd
Write-Host ""

if ($script:sharedHint) {
    foreach ($line in $script:sharedHint) {
        Write-Host $line
    }
    Write-Host ""
}

if (-not $isInfra) {
    $levelHint = Get-StudyLevelLabel -StudyLevels $StudyLevel
    Write-Host "# then tag (same version):"
    Write-Host ".\scripts\tag-uni.ps1 -Pick $Pick -StudyLevel $levelHint -Version $version"
}
