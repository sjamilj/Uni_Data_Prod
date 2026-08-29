# Re-run Stage 2a entry requirements only (Bangladesh JSON) for all extracted courses.
#
# Modes:
#   Default     — call Ollama for entry_requirement on every course (~hours for 317)
#   -MergeOnly  — fix from bangladesh-entry JSON only, no LLM (~seconds)
#
# Examples:
#   .\run_rerun_entry_requirements.ps1 -University "Anglia Ruskin University - ARU" -MergeOnly -ExportDevCsv
#   .\run_rerun_entry_requirements.ps1 -University "Anglia Ruskin University - ARU" -Resume -ExportDevCsv
#   .\run_rerun_entry_requirements.ps1 -University "Anglia Ruskin University - ARU" -Limit 5

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$University,

    [switch]$Resume,
    [int]$Limit = 0,
    [switch]$MergeOnly,
    [switch]$ExportDevCsv,
    [string]$Model = "",
    [string]$OllamaHost = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$CodeDir = Join-Path (Join-Path $RepoRoot $University) "code"
$Script = Join-Path $RepoRoot "shared\rerun_entry_requirements.py"

if (-not (Test-Path $Script)) {
    throw "Missing script: $Script"
}

$argsList = @($CodeDir)
if ($Resume) { $argsList += "--resume" }
if ($Limit -gt 0) { $argsList += @("--limit", $Limit) }
if ($MergeOnly) { $argsList += "--merge-only" }
if ($ExportDevCsv) { $argsList += @("--normalize", "--export-dev-csv") }
if ($Model) { $argsList += @("--model", $Model) }
if ($OllamaHost) { $argsList += @("--host", $OllamaHost) }

Write-Host "==> Entry requirements rerun" -ForegroundColor Cyan
Write-Host "python -u $Script $($argsList -join ' ')"

Push-Location (Join-Path $RepoRoot "shared")
try {
    python -u $Script @argsList
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
