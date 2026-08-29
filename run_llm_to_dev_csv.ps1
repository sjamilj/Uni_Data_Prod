# Run F1 pipeline phases 3-5: llm_extract -> normalize -> dev_courses CSV.
#
# Requires: Ollama running, clean/courses/*.md and clean/uni/*.md from Phase 2.
#
# Resume after power cut: re-run with -Resume (skips completed courses in extraction_progress.json).
#
# Phase 3: shared/llm_extract.py           -> output/extracted/{slug}/, output/extracted_courses.csv
# Phase 4: shared/normalize_admission_data.py -> output/extracted/{slug}/normalized.json
# Phase 5: shared/export_dev_courses.py    -> output/dev_courses_{UNIVERSITY_NAME}.csv
#
# Examples:
#   .\run_llm_to_dev_csv.ps1 -University "Anglia Ruskin University - ARU" -Resume
#   .\run_llm_to_dev_csv.ps1 -University "Anglia Ruskin University - ARU" -Limit 5 -Resume
#   .\run_llm_to_dev_csv.ps1 -University "Anglia Ruskin University - ARU" -SkipExtract
#   .\run_llm_to_dev_csv.ps1 -University "Anglia Ruskin University - ARU" -ExtractOnly -Resume

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$University,

    [switch]$Resume,
    [int]$Limit = 0,
    [switch]$BuildIndex,
    [switch]$SkipExtract,
    [switch]$SkipNormalize,
    [switch]$ExtractOnly,
    [switch]$SkipStage1,
    [string]$Model = "",
    [string]$OllamaHost = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$UniversityRoot = Join-Path $RepoRoot $University
$CodeDir = Join-Path $UniversityRoot "code"
$OutputDir = Join-Path $UniversityRoot "output"
$ExtractScript = Join-Path $RepoRoot "shared\llm_extract.py"
$NormalizeScript = Join-Path $RepoRoot "shared\normalize_admission_data.py"
$ExportScript = Join-Path $RepoRoot "shared\export_dev_courses.py"
$CourseIndexCsv = Join-Path $OutputDir "courses.csv"
$ExtractProgressFile = Join-Path $OutputDir "extracted\extraction_progress.json"

function Get-ExtractionProgress {
    $info = [ordered]@{
        Completed    = 0
        Failed       = 0
        TotalMd      = 0
        IndexCourses = 0
    }

    $coursesDir = Join-Path $OutputDir "clean\courses"
    if (Test-Path $coursesDir) {
        $info.TotalMd = @(Get-ChildItem $coursesDir -Filter "*.md" -File -Recurse).Count
    }
    if (Test-Path $CourseIndexCsv) {
        $info.IndexCourses = @(Import-Csv $CourseIndexCsv).Count
    }

    if (Test-Path $ExtractProgressFile) {
        try {
            $progress = Get-Content $ExtractProgressFile -Raw | ConvertFrom-Json
            if ($progress.completed) { $info.Completed = @($progress.completed).Count }
            if ($progress.failed) { $info.Failed = @($progress.failed).Count }
        }
        catch {
            Write-Host "Warning: could not read $ExtractProgressFile" -ForegroundColor Yellow
        }
    }

    return [pscustomobject]$info
}

function Show-ExtractionStatus {
    param([pscustomobject]$Progress)

    Write-Host ""
    Write-Host "LLM extract status ($OutputDir):" -ForegroundColor Cyan
    Write-Host "  clean markdown   : $($Progress.TotalMd) file(s)"
    if ($Progress.IndexCourses -gt 0) {
        Write-Host "  index courses    : $($Progress.IndexCourses) programme(s)"
        if ($Progress.TotalMd -gt $Progress.IndexCourses) {
            $dupes = $Progress.TotalMd - $Progress.IndexCourses
            Write-Host "  url duplicates   : $dupes variant file(s) ignored by index" -ForegroundColor Yellow
        }
    }
    Write-Host "  extracted (done) : $($Progress.Completed)"
    Write-Host "  failed           : $($Progress.Failed)"
    $target = if ($Progress.IndexCourses -gt 0) { $Progress.IndexCourses } else { $Progress.TotalMd }
    if ($target -gt 0 -and $Progress.Completed -gt 0) {
        $remaining = [Math]::Max(0, $target - $Progress.Completed)
        Write-Host "  extract left     : ~$remaining (with -Resume)" -ForegroundColor Green
    }
}

function Invoke-PythonStep {
    param(
        [string]$Label,
        [string[]]$Arguments
    )

    Write-Host ""
    Write-Host "==> $Label" -ForegroundColor Cyan
    Write-Host "python -u $($Arguments -join ' ')"
    $env:PYTHONUNBUFFERED = "1"
    & python -u @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed ($Label): exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path $CodeDir)) {
    throw "University code folder not found: $CodeDir"
}
foreach ($script in @($ExtractScript, $NormalizeScript, $ExportScript)) {
    if (-not (Test-Path $script)) {
        throw "Missing script: $script"
    }
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "python is not on PATH. Install Python or use 'py -3'."
}

if (-not $SkipExtract) {
    $coursesDir = Join-Path $OutputDir "clean\courses"
    $courseMdCount = 0
    if (Test-Path $coursesDir) {
        $courseMdCount = @(Get-ChildItem $coursesDir -Filter "*.md" -File -Recurse).Count
    }
    if ($courseMdCount -eq 0) {
        throw "No clean/courses/*.md in $coursesDir. Run Phase 2 first."
    }

    $ollamaUri = if ($OllamaHost) { $OllamaHost.TrimEnd("/") } else { "http://localhost:11434" }
    try {
        Invoke-WebRequest -Uri $ollamaUri -UseBasicParsing -TimeoutSec 3 | Out-Null
    }
    catch {
        throw "Ollama is not reachable at $ollamaUri. Start Ollama, then re-run."
    }
}

$extractionProgress = Get-ExtractionProgress

Write-Host "Repo root  : $RepoRoot"
Write-Host "University : $University"
Write-Host "Code dir   : $CodeDir"
Write-Host "Python     : $($python.Source)"
if ($Resume) {
    Show-ExtractionStatus -Progress $extractionProgress
    Write-Host "Mode       : RESUME (skips courses in extraction_progress.json)" -ForegroundColor Green
}

$limitArgs = @()
if ($Limit -gt 0) {
    $limitArgs = @("--limit", $Limit)
}

if (-not $SkipExtract) {
    $needsIndex = $BuildIndex.IsPresent -or -not (Test-Path $CourseIndexCsv)
    if (-not $needsIndex -and (Test-Path $CourseIndexCsv)) {
        $csvRows = @(Import-Csv $CourseIndexCsv).Count
        if ($courseMdCount -gt 0 -and $csvRows -gt $courseMdCount) {
            Write-Host "courses.csv has $csvRows row(s) but clean/courses has $courseMdCount file(s) - rebuilding index" -ForegroundColor Yellow
            $needsIndex = $true
        }
    }
    if ($needsIndex) {
        $indexArgs = @($ExtractScript, $CodeDir, "--build-index")
        Invoke-PythonStep -Label "Build courses.csv index from clean/courses" -Arguments $indexArgs
    }

    $extractArgs = @($ExtractScript, $CodeDir)
    if ($Resume) { $extractArgs += "--resume" }
    if ($Limit -gt 0) { $extractArgs += @("--limit", $Limit) }
    if ($SkipStage1) { $extractArgs += "--skip-stage1" }
    if ($Model) { $extractArgs += @("--model", $Model) }
    if ($OllamaHost) { $extractArgs += @("--host", $OllamaHost) }

    Invoke-PythonStep -Label "Phase 3 - LLM extract" -Arguments $extractArgs
}
else {
    Write-Host ""
    Write-Host "==> Phase 3 skipped (-SkipExtract)" -ForegroundColor Yellow
}

if ($ExtractOnly) {
    Write-Host ""
    Write-Host "Done (-ExtractOnly). Next:" -ForegroundColor Green
    Write-Host "  .\run_llm_to_dev_csv.ps1 -University `"$University`" -SkipExtract"
    return
}

if (-not $SkipNormalize) {
    $normalizeArgs = @($NormalizeScript, $CodeDir) + $limitArgs
    Invoke-PythonStep -Label "Phase 4 - normalize extracted JSON" -Arguments $normalizeArgs
}
else {
    Write-Host ""
    Write-Host "==> Phase 4 skipped (-SkipNormalize)" -ForegroundColor Yellow
}

$exportArgs = @($ExportScript, $CodeDir) + $limitArgs
Invoke-PythonStep -Label "Phase 5 - export dev_courses CSV" -Arguments $exportArgs

$devCsvPattern = Join-Path $OutputDir "dev_courses_*.csv"
$devCsv = Get-ChildItem $devCsvPattern -ErrorAction SilentlyContinue | Select-Object -First 1

Write-Host ""
Write-Host "Done." -ForegroundColor Green
if ($devCsv) {
    Write-Host "  $($devCsv.FullName)"
}
