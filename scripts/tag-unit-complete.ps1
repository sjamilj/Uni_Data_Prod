# Back-compat wrapper for full-university tags. Prefer tag-uni.ps1.
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

if ($Unit -notmatch '^unit-\d{2}$') {
    throw "Unit must look like unit-03 (got '$Unit')"
}
if ($Slug -notmatch '^[a-z0-9-]+$') {
    throw "Slug must be lowercase letters, digits, or hyphens (got '$Slug')"
}

& "$PSScriptRoot/tag-uni.ps1" -Pick $Slug -Version $Version
