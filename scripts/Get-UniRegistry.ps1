# Load university unit/slug/folder metadata from UNIVERSITIES_REGISTRY.md.
# Dot-source this file: . "$PSScriptRoot/Get-UniRegistry.ps1"

function Get-UniRegistry {
    param(
        [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    )

    $registryPath = Join-Path $RepoRoot "UNIVERSITIES_REGISTRY.md"
    if (-not (Test-Path -LiteralPath $registryPath)) {
        throw "Registry not found: $registryPath"
    }

    $rows = @()
    foreach ($line in Get-Content -LiteralPath $registryPath) {
        if ($line -match '^\|\s*(unit-\d{2})\s*\|\s*([a-z0-9-]+)\s*\|\s*([^|]+?)\s*\|\s*(\w+)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|') {
            $rows += [pscustomobject]@{
                Unit     = $Matches[1].Trim()
                Slug     = $Matches[2].Trim()
                Folder   = $Matches[3].Trim()
                Status   = $Matches[4].Trim()
                Tag      = $Matches[5].Trim()
                Commit   = $Matches[6].Trim()
                Scope    = "$($Matches[1].Trim())/$($Matches[2].Trim())"
            }
            continue
        }
        if ($line -notmatch '^\|\s*(unit-\d{2})\s*\|\s*([a-z0-9-]+)\s*\|\s*([^|]+?)\s*\|\s*(\w+)\s*\|') {
            continue
        }
        $rows += [pscustomobject]@{
            Unit     = $Matches[1].Trim()
            Slug     = $Matches[2].Trim()
            Folder   = $Matches[3].Trim()
            Status   = $Matches[4].Trim()
            Tag      = ""
            Commit   = ""
            Scope    = "$($Matches[1].Trim())/$($Matches[2].Trim())"
        }
    }

    if (-not $rows) {
        throw "No university rows parsed from $registryPath"
    }

    return $rows
}

function Resolve-UniEntry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Pick,

        [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    )

    $registry = Get-UniRegistry -RepoRoot $RepoRoot
    $pickNorm = $Pick.Trim().ToLower()

    $entry = $registry | Where-Object {
        $_.Unit -eq $pickNorm -or
        $_.Slug -eq $pickNorm -or
        $_.Folder.ToLower() -eq $pickNorm -or
        $_.Scope -eq $pickNorm
    } | Select-Object -First 1

    if (-not $entry) {
        $choices = ($registry | ForEach-Object { "$($_.Unit) $($_.Slug) $($_.Folder)" }) -join "`n  "
        throw "Unknown university '$Pick'. Use unit-NN, slug, folder name, or unit-NN/slug.`n  $choices"
    }

    return $entry
}

function Expand-StudyLevelInput {
    param(
        [string[]]$StudyLevels
    )

    if (-not $StudyLevels -or $StudyLevels.Count -eq 0) {
        return @("all")
    }

    $expanded = @()
    foreach ($raw in $StudyLevels) {
        foreach ($part in ($raw -split ',')) {
            $token = $part.Trim()
            if ($token) {
                $expanded += $token
            }
        }
    }

    if (-not $expanded) {
        return @("all")
    }

    return $expanded
}

function Get-StudyLevelLabel {
    param(
        [string[]]$StudyLevels
    )

    $canonical = @(
        "foundation",
        "undergraduate",
        "postgraduate",
        "postgraduate_research"
    )

    $inputs = Expand-StudyLevelInput -StudyLevels $StudyLevels
    if ($inputs -contains "all") {
        return "all"
    }

    $levels = @()
    foreach ($raw in $inputs) {
        $level = $raw.Trim().ToLower().Replace("-", "_")
        switch ($level) {
            "foundation" { $levels += "foundation"; continue }
            "undergraduate" { $levels += "undergraduate"; continue }
            "ug" { $levels += "undergraduate"; continue }
            "postgraduate" { $levels += "postgraduate"; continue }
            "pg" { $levels += "postgraduate"; continue }
            "postgraduate_research" { $levels += "postgraduate_research"; continue }
            "pgr" { $levels += "postgraduate_research"; continue }
            default {
                throw "Unknown study level '$raw'. Use foundation, undergraduate, postgraduate, postgraduate_research, or all."
            }
        }
    }

    $ordered = $canonical | Where-Object { $levels -contains $_ }
    if (-not $ordered) {
        throw "No valid study levels in: $($StudyLevels -join ', ')"
    }

    return ($ordered -join "-")
}

function Format-StudyLevelCommitPhrase {
    param(
        [string[]]$StudyLevels
    )

    $label = Get-StudyLevelLabel -StudyLevels $StudyLevels
    if ($label -eq "all") {
        return "complete pipeline and export dev_courses CSV"
    }

    $pretty = $label -replace "postgraduate_research", "postgraduate research"
    $pretty = $pretty -replace "-", " and "
    return "complete $pretty pipeline"
}

function Get-UniTagName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Slug,

        [Parameter(Mandatory = $true)]
        [string]$Version,

        [string[]]$StudyLevels
    )

    $version = $Version.Trim()
    if ($version -notmatch '^v') {
        $version = "v$version"
    }

    $label = Get-StudyLevelLabel -StudyLevels $StudyLevels
    if ($label -eq "all") {
        return "uni/$Slug/$version"
    }

    return "uni/$Slug/$label/$version"
}

function Get-LatestVersionFromHistory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Slug,

        [string[]]$StudyLevels,

        [Parameter(Mandatory = $true)]
        [string]$Scope,

        [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    )

    $label = Get-StudyLevelLabel -StudyLevels $StudyLevels
    $versions = @()
    $levelPhrase = ""
    if ($label -ne "all") {
        $levelPhrase = $label -replace "postgraduate_research", "postgraduate research"
        $levelPhrase = $levelPhrase -replace "-", " and "
    }

    if ($label -eq "all") {
        $tagPattern = "uni/$Slug/v*"
    } else {
        $tagPattern = "uni/$Slug/$label/v*"
    }

    foreach ($tag in @(git -C $RepoRoot tag -l $tagPattern)) {
        if ($tag -match '/v(\d+\.\d+\.\d+)$') {
            $versions += [version]$Matches[1]
        }
    }

    $logLines = @(git -C $RepoRoot log --oneline --all --grep="$Scope" 2>$null)
    foreach ($line in $logLines) {
        if ($label -ne "all" -and $levelPhrase -and $line -notmatch [regex]::Escape($levelPhrase)) {
            continue
        }
        if ($line -match '\bv(\d+\.\d+\.\d+)\b') {
            $versions += [version]$Matches[1]
        }
    }

    if (-not $versions) {
        $hasFeat = $false
        foreach ($line in $logLines) {
            if ($line -notmatch "feat\($([regex]::Escape($Scope))\)") {
                continue
            }
            if ($label -ne "all" -and $levelPhrase -and $line -notmatch [regex]::Escape($levelPhrase)) {
                continue
            }
            $hasFeat = $true
            break
        }
        if ($hasFeat) {
            return [version]"1.0.0"
        }
    }

    if (-not $versions) {
        return $null
    }

    return ($versions | Sort-Object -Descending | Select-Object -First 1)
}

function Resolve-NextCommitVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Slug,

        [string[]]$StudyLevels,

        [Parameter(Mandatory = $true)]
        [string]$Type,

        [Parameter(Mandatory = $true)]
        [string]$Scope,

        [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    )

    $latest = Get-LatestVersionFromHistory -Slug $Slug -StudyLevels $StudyLevels -Scope $Scope -RepoRoot $RepoRoot

    if (-not $latest) {
        if ($Type -eq "feat") {
            return "1.0.0"
        }
        return "1.0.1"
    }

    return "{0}.{1}.{2}" -f $latest.Major, $latest.Minor, ($latest.Build + 1)
}

function Format-VersionedCommitMessage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseMessage,

        [Parameter(Mandatory = $true)]
        [string]$Version
    )

    $v = $Version.Trim().TrimStart("v")
    return "$BaseMessage v$v"
}

function Get-LatestUniTagVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Slug,

        [string[]]$StudyLevels,

        [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    )

    $label = Get-StudyLevelLabel -StudyLevels $StudyLevels
    if ($label -eq "all") {
        $pattern = "uni/$Slug/v*"
    } else {
        $pattern = "uni/$Slug/$label/v*"
    }

    $tags = git -C $RepoRoot tag -l $pattern
    if (-not $tags) {
        return "1.0.0"
    }

    $versions = foreach ($tag in $tags) {
        if ($tag -match '/v(\d+\.\d+\.\d+)$') {
            [version]$Matches[1]
        }
    }

    if (-not $versions) {
        return "1.0.0"
    }

    $latest = ($versions | Sort-Object -Descending | Select-Object -First 1)
    return "{0}.{1}.{2}" -f $latest.Major, $latest.Minor, ($latest.Build + 1)
}

function Get-UniTags {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Slug,

        [string]$Unit = "",

        [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    )

    $tags = @(git -C $RepoRoot tag -l "uni/$Slug/*")
    if ($Unit) {
        $unitTag = git -C $RepoRoot tag -l $Unit
        if ($unitTag) {
            $tags += $unitTag
        }
    }

    return $tags | Select-Object -Unique | Sort-Object
}

function Get-StudyLevelCommitPhrase {
    param(
        [string[]]$StudyLevels
    )

    $label = Get-StudyLevelLabel -StudyLevels $StudyLevels
    if ($label -eq "all") {
        return ""
    }

    $phrase = $label -replace "postgraduate_research", "postgraduate research"
    return $phrase -replace "-", " and "
}

function Test-CommitMatchesStudyLevels {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Subject,

        [string[]]$StudyLevels
    )

    $phrase = Get-StudyLevelCommitPhrase -StudyLevels $StudyLevels
    if (-not $phrase) {
        return $true
    }

    return $Subject -match [regex]::Escape($phrase)
}

function Get-UniCommitsFromHistory {
    param(
        [Parameter(Mandatory = $true)]
        $Entry,

        [string[]]$StudyLevels = @("all"),

        [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    )

    $scope = $Entry.Scope
    $lines = @(git -C $RepoRoot log --format="%H%x09%s" --all --grep="$scope" 2>$null)
    $commits = @()

    foreach ($line in $lines) {
        if (-not $line) { continue }
        $parts = $line -split "`t", 2
        $sha = $parts[0]
        $subject = if ($parts.Count -gt 1) { $parts[1] } else { "" }
        if ($subject -notmatch "\($([regex]::Escape($scope))\)") {
            continue
        }
        if (-not (Test-CommitMatchesStudyLevels -Subject $subject -StudyLevels $StudyLevels)) {
            continue
        }

        $version = ""
        if ($subject -match '\bv(\d+\.\d+\.\d+)\b') {
            $version = $Matches[1]
        }

        $priority = 0
        if ($subject -match '^(feat|fix|wip)\(') { $priority += 10 }
        if ($subject -match 'complete') { $priority += 5 }

        $commits += [pscustomobject]@{
            Sha      = $sha
            Subject  = $subject
            Version  = $version
            Priority = $priority
        }
    }

    return $commits |
        Sort-Object Priority -Descending |
        Sort-Object { if ($_.Version) { [version]$_.Version } else { [version]"0.0.0" } } -Descending
}

function Resolve-CheckoutCommitFromHistory {
    param(
        [Parameter(Mandatory = $true)]
        $Entry,

        [string[]]$StudyLevels = @("all"),

        [string]$Version = "",

        [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    )

    $commits = Get-UniCommitsFromHistory -Entry $Entry -StudyLevels $StudyLevels -RepoRoot $RepoRoot
    if (-not $commits) {
        return $null
    }

    if ($Version.Trim()) {
        $wanted = $Version.Trim().TrimStart("v")
        $match = $commits | Where-Object { $_.Version -eq $wanted } | Select-Object -First 1
        if ($match) {
            return $match.Sha
        }
        return $null
    }

    if ($Entry.Commit) {
        $registryCommit = $Entry.Commit.Trim()
        $exists = git -C $RepoRoot cat-file -e "$registryCommit^{commit}" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $registryCommit
        }
    }

    return ($commits | Select-Object -First 1).Sha
}

function Resolve-CheckoutRef {
    param(
        [Parameter(Mandatory = $true)]
        $Entry,

        [string[]]$StudyLevels = @("all"),

        [string]$Version = "",

        [string]$Tag = "",

        [string]$Commit = "",

        [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    )

    if ($Commit.Trim()) {
        $sha = $Commit.Trim()
        git -C $RepoRoot cat-file -e "$sha^{commit}" 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Commit not found: $sha"
        }
        return $sha
    }

    if ($Tag.Trim()) {
        $exists = git -C $RepoRoot tag -l $Tag.Trim()
        if (-not $exists) {
            throw "Tag not found: $($Tag.Trim())"
        }
        return $Tag.Trim()
    }

    if ($Version.Trim()) {
        $tagName = Get-UniTagName -Slug $Entry.Slug -Version $Version.Trim() -StudyLevels $StudyLevels
        $exists = git -C $RepoRoot tag -l $tagName
        if ($exists) {
            return $tagName
        }
        $commit = Resolve-CheckoutCommitFromHistory -Entry $Entry -StudyLevels $StudyLevels -Version $Version -RepoRoot $RepoRoot
        if ($commit) {
            return $commit
        }
        throw "No tag or commit found for version $($Version.Trim()) on $($Entry.Folder)."
    }

    if ($Entry.Tag) {
        $exists = git -C $RepoRoot tag -l $Entry.Tag
        if ($exists) {
            return $Entry.Tag
        }
    }

    $label = Get-StudyLevelLabel -StudyLevels $StudyLevels
    if ($label -eq "all") {
        $patterns = @("uni/$($Entry.Slug)/v*", "uni/$($Entry.Slug)/*")
    } else {
        $patterns = @("uni/$($Entry.Slug)/$label/v*")
    }

    $candidates = @()
    foreach ($pattern in $patterns) {
        foreach ($name in @(git -C $RepoRoot tag -l $pattern)) {
            if ($name -match '/v(\d+\.\d+\.\d+)$') {
                $candidates += [pscustomobject]@{
                    Name    = $name
                    Version = [version]$Matches[1]
                }
            }
        }
        if ($candidates) { break }
    }

    if ($candidates) {
        return ($candidates | Sort-Object Version -Descending | Select-Object -First 1).Name
    }

    $unitTag = git -C $RepoRoot tag -l $Entry.Unit
    if ($unitTag) {
        return $Entry.Unit
    }

    $commit = Resolve-CheckoutCommitFromHistory -Entry $Entry -StudyLevels $StudyLevels -RepoRoot $RepoRoot
    if ($commit) {
        return $commit
    }

    $available = Get-UniTags -Slug $Entry.Slug -Unit $Entry.Unit -RepoRoot $RepoRoot
    $history = Get-UniCommitsFromHistory -Entry $Entry -StudyLevels $StudyLevels -RepoRoot $RepoRoot
    $hintParts = @()
    if ($available) {
        $hintParts += "Available tags:`n  $($available -join "`n  ")"
    }
    if ($history) {
        $historyLines = ($history | Select-Object -First 5 | ForEach-Object { "$($_.Sha.Substring(0,7)) $($_.Subject)" }) -join "`n  "
        $hintParts += "Commits from git log --grep=$($Entry.Scope):`n  $historyLines"
    } else {
        $hintParts += "No matching commits in git history. Look for feat($($Entry.Scope)): ... v1.0.0"
    }
    if (-not $available) {
        $hintParts += "Or create a tag: .\scripts\tag-uni.cmd -Pick $($Entry.Slug)"
    }

    throw "No checkout ref for $($Entry.Folder). $($hintParts -join "`n")"
}

function Resolve-CheckoutTag {
    param(
        [Parameter(Mandatory = $true)]
        $Entry,

        [string[]]$StudyLevels = @("all"),

        [string]$Version = "",

        [string]$Tag = "",

        [string]$Commit = "",

        [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    )

    return Resolve-CheckoutRef -Entry $Entry -StudyLevels $StudyLevels -Version $Version -Tag $Tag -Commit $Commit -RepoRoot $RepoRoot
}
