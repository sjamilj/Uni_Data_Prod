# Phases 3-5 for ONE clean course markdown: llm_extract -> normalize -> dev_courses CSV.
#
# Requires: Ollama running, clean/uni/*.md, and the target file under output/clean/courses/.
#
# Examples:
#   .\run_llm_to_dev_csv_one.ps1 -University "University of Bedfordshire" -CleanMd "undergraduate\adult-nursing-bsc.md"
#   .\run_llm_to_dev_csv_one.ps1 -University "University of Bedfordshire" -CleanMd "E:\...\output\clean\courses\postgraduate\accounting-and-business-finance.md"
#   .\run_llm_to_dev_csv_one.ps1 -University "University of Bedfordshire" -CleanMd adult-nursing-bsc.md -SkipNormalize

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$University,

    [Parameter(Mandatory = $true, Position = 1)]
    [string]$CleanMd,

    [switch]$SkipNormalize,
    [switch]$SkipExport,
    [switch]$SkipStage1,
    [switch]$BuildIndex,
    [string]$Model = "",
    [string]$OllamaHost = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$UniversityRoot = Join-Path $RepoRoot $University
$CodeDir = Join-Path $UniversityRoot "code"
$OutputDir = Join-Path $UniversityRoot "output"
$CoursesDir = Join-Path $OutputDir "clean\courses"
$ExtractScript = Join-Path $RepoRoot "shared\llm_extract.py"
$NormalizeScript = Join-Path $RepoRoot "shared\normalize_admission_data.py"
$ExportScript = Join-Path $RepoRoot "shared\export_dev_courses.py"
$CourseIndexCsv = Join-Path $OutputDir "courses.csv"

function Get-RelativePathFromRoot {
    param(
        [string]$Root,
        [string]$FullPath
    )

    $rootFull = [System.IO.Path]::GetFullPath($Root)
    if (-not $rootFull.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $rootFull += [System.IO.Path]::DirectorySeparatorChar
    }
    $full = [System.IO.Path]::GetFullPath($FullPath)
    if ($full.StartsWith($rootFull, [StringComparison]::OrdinalIgnoreCase)) {
        return $full.Substring($rootFull.Length)
    }
    throw "Path is not under root: $FullPath"
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

function Resolve-CleanMdForIndex {
    param(
        [string]$InputPath,
        [string]$CoursesRoot
    )

    if ([System.IO.Path]::IsPathRooted($InputPath)) {
        $full = [System.IO.Path]::GetFullPath($InputPath)
        $coursesRootFull = [System.IO.Path]::GetFullPath($CoursesRoot)
        if (-not $full.StartsWith($coursesRootFull, [StringComparison]::OrdinalIgnoreCase)) {
            throw "CleanMd must be under $CoursesRoot (got $full)"
        }
        $rel = $full.Substring($coursesRootFull.Length).TrimStart('\', '/')
        return $rel.Replace('\', '/')
    }

    $candidate = Join-Path $CoursesRoot $InputPath
    if (Test-Path $candidate) {
        return (Get-RelativePathFromRoot -Root $CoursesRoot -FullPath $candidate).Replace('\', '/')
    }

    $name = [System.IO.Path]::GetFileName($InputPath)
    $found = @(Get-ChildItem $CoursesRoot -Filter $name -File -Recurse -ErrorAction SilentlyContinue)
    if ($found.Count -eq 1) {
        return (Get-RelativePathFromRoot -Root $CoursesRoot -FullPath $found[0].FullName).Replace('\', '/')
    }
    if ($found.Count -gt 1) {
        $list = ($found | ForEach-Object { (Get-RelativePathFromRoot -Root $CoursesRoot -FullPath $_.FullName).Replace('\', '/') }) -join ", "
        throw "Multiple clean markdown files named $name. Use a path relative to clean/courses: $list"
    }

    throw "Clean markdown not found: $InputPath (under $CoursesRoot)"
}

if (-not (Test-Path $CodeDir)) {
    throw "University code folder not found: $CodeDir"
}
if (-not (Test-Path $CoursesDir)) {
    throw "Missing $CoursesDir - run download/clean first."
}
foreach ($script in @($ExtractScript, $NormalizeScript, $ExportScript)) {
    if (-not (Test-Path $script)) {
        throw "Missing script: $script"
    }
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "python is not on PATH."
}

$mdRel = Resolve-CleanMdForIndex -InputPath $CleanMd -CoursesRoot $CoursesDir
$mdOnDisk = Join-Path $CoursesDir ($mdRel.Replace('/', '\'))
if (-not (Test-Path $mdOnDisk)) {
    throw "Resolved path does not exist: $mdOnDisk"
}

$ollamaUri = if ($OllamaHost) { $OllamaHost.TrimEnd("/") } else { "http://localhost:11434" }
try {
    Invoke-WebRequest -Uri $ollamaUri -UseBasicParsing -TimeoutSec 3 | Out-Null
}
catch {
    throw "Ollama is not reachable at $ollamaUri. Start Ollama, then re-run."
}

Write-Host "Repo root  : $RepoRoot"
Write-Host "University : $University"
Write-Host "Code dir   : $CodeDir"
Write-Host "Clean md   : $mdRel"

$needsIndex = $BuildIndex.IsPresent -or -not (Test-Path $CourseIndexCsv)
if ($needsIndex) {
    Invoke-PythonStep -Label "Build courses.csv index" -Arguments @($ExtractScript, $CodeDir, "--build-index")
}

$extractArgs = @($ExtractScript, $CodeDir, "--md-file", $mdRel)
if ($SkipStage1) { $extractArgs += "--skip-stage1" }
if ($Model) { $extractArgs += @("--model", $Model) }
if ($OllamaHost) { $extractArgs += @("--host", $OllamaHost) }

Invoke-PythonStep -Label "Phase 3 - LLM extract (one course)" -Arguments $extractArgs

if (-not $SkipNormalize) {
    Invoke-PythonStep -Label "Phase 4 - normalize (all extracted; includes this course)" -Arguments @($NormalizeScript, $CodeDir)
}
else {
    Write-Host ""
    Write-Host "==> Phase 4 skipped (-SkipNormalize)" -ForegroundColor Yellow
}

if (-not $SkipExport) {
    Invoke-PythonStep -Label "Phase 5 - export dev_courses CSV" -Arguments @($ExportScript, $CodeDir)
}
else {
    Write-Host ""
    Write-Host "==> Phase 5 skipped (-SkipExport)" -ForegroundColor Yellow
}

$devCsvPattern = Join-Path $OutputDir "dev_courses_*.csv"
$devCsv = Get-ChildItem $devCsvPattern -ErrorAction SilentlyContinue | Select-Object -First 1

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "  markdown : clean/courses/$mdRel"
if ($devCsv) {
    Write-Host "  CSV      : $($devCsv.FullName)"
}
