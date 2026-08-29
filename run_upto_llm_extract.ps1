# Run F1 pipeline phases 1-2 only (stops before llm_extract).
#
# Resume after power cut / crash: re-run with -Resume (or same command without -Fresh).
# Progress is stored in {University}/output/scrape_progress.json
#   - Phase 1: listing_completed, group_state, course_urls
#   - Phase 2 download: downloaded_urls (skips already saved HTML)
#   - Phase 2 clean: re-processes all downloaded HTML (fast vs download)
#
# Phase 1: shared/scrape_course_urls.py      -> output/course_urls.csv
# Phase 2: shared/download_and_clean_course_pages.py -> output/course_pages/, output/clean/courses/
#
# Examples:
#   .\run_upto_llm_extract.ps1 -University "Anglia Ruskin University - ARU"
#   .\run_upto_llm_extract.ps1 -University "Anglia Ruskin University - ARU" -Resume
#   .\run_upto_llm_extract.ps1 -University "Aston University" -Limit 5
#   .\run_upto_llm_extract.ps1 -University "Anglia Ruskin University - ARU" -Fresh
#   .\run_upto_llm_extract.ps1 -University "Anglia Ruskin University - ARU" -Resume -SkipScrape -CleanOnly

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$University,

    [switch]$Resume,
    [switch]$Fresh,
    [switch]$ScrapeFresh,
    [switch]$DownloadFresh,
    [int]$Limit = 0,
    [switch]$SkipScrape,
    [switch]$CleanOnly,
    [switch]$DownloadOnly,
    [switch]$RefreshUni
)

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$UniversityRoot = Join-Path $RepoRoot $University
$CodeDir = Join-Path $UniversityRoot "code"
$OutputDir = Join-Path $UniversityRoot "output"
$ScrapeScript = Join-Path $RepoRoot "shared\scrape_course_urls.py"
$DownloadScript = Join-Path $RepoRoot "shared\download_and_clean_course_pages.py"
$ProgressFile = Join-Path $OutputDir "scrape_progress.json"
$CourseUrlsCsv = Join-Path $OutputDir "course_urls.csv"

function Get-PipelineProgress {
    $info = [ordered]@{
        Phase           = "unknown"
        TotalUrls       = 0
        DownloadedUrls  = 0
        FailedUrls      = 0
        ScrapeComplete  = $false
    }

    if (Test-Path $CourseUrlsCsv) {
        $lines = Get-Content $CourseUrlsCsv | Where-Object { $_.Trim() -and $_ -notmatch '^\s*#' }
        $info.TotalUrls = @($lines).Count
    }

    if (Test-Path $ProgressFile) {
        try {
            $progress = Get-Content $ProgressFile -Raw | ConvertFrom-Json
            if ($progress.phase) { $info.Phase = [string]$progress.phase }
            if ($progress.downloaded_urls) { $info.DownloadedUrls = @($progress.downloaded_urls).Count }
            if ($progress.failed_urls) { $info.FailedUrls = @($progress.failed_urls).Count }
            $info.ScrapeComplete = ($info.Phase -eq "urls_complete")
        }
        catch {
            Write-Host "Warning: could not read $ProgressFile" -ForegroundColor Yellow
        }
    }

    return [pscustomobject]$info
}

function Show-ResumeStatus {
    param([pscustomobject]$Progress)

    Write-Host ""
    Write-Host "Resume status ($OutputDir):" -ForegroundColor Cyan
    Write-Host "  scrape phase     : $($Progress.Phase)"
    Write-Host "  course URLs      : $($Progress.TotalUrls)"
    Write-Host "  downloaded HTML  : $($Progress.DownloadedUrls)"
    Write-Host "  failed downloads : $($Progress.FailedUrls)"
    if ($Progress.ScrapeComplete) {
        Write-Host "  Phase 1 complete - will skip URL scrape" -ForegroundColor Green
    }
    if ($Progress.DownloadedUrls -gt 0 -and $Progress.TotalUrls -gt 0) {
        $remaining = [Math]::Max(0, $Progress.TotalUrls - $Progress.DownloadedUrls)
        Write-Host "  download left    : ~$remaining (failed URLs retried)" -ForegroundColor Green
    }
}

function Invoke-PythonStep {
    param(
        [string]$Label,
        [string[]]$Arguments
    )

    Write-Host ""
    Write-Host "==> $Label" -ForegroundColor Cyan
    Write-Host "python $($Arguments -join ' ')"
    & python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed ($Label): exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path $CodeDir)) {
    throw "University code folder not found: $CodeDir"
}
if (-not (Test-Path $ScrapeScript)) {
    throw "Missing script: $ScrapeScript"
}
if (-not (Test-Path $DownloadScript)) {
    throw "Missing script: $DownloadScript"
}

if ($Resume -and $Fresh) {
    throw "-Resume and -Fresh cannot be used together. Use -Resume after a power cut; use -Fresh to start over."
}
if ($DownloadOnly -and $CleanOnly) {
    throw "-DownloadOnly and -CleanOnly cannot be used together."
}

$pipelineProgress = Get-PipelineProgress
$scrapeFresh = (-not $Resume) -and ($ScrapeFresh.IsPresent -or $Fresh.IsPresent)
$downloadFresh = (-not $Resume) -and ($DownloadFresh.IsPresent -or $Fresh.IsPresent)

if ($Resume) {
    Show-ResumeStatus -Progress $pipelineProgress
    if ($pipelineProgress.ScrapeComplete -and -not $SkipScrape) {
        $SkipScrape = $true
    }
}

Write-Host "University : $University"
Write-Host "Code dir   : $CodeDir"
if ($Resume) {
    Write-Host "Mode       : RESUME (keeps scrape_progress.json, skips finished downloads)" -ForegroundColor Green
}

if (-not $SkipScrape) {
    $scrapeArgs = @($ScrapeScript, "--code-dir", $CodeDir)
    if ($scrapeFresh) {
        $scrapeArgs += "--fresh"
    }
    Invoke-PythonStep -Label "Phase 1 - scrape course URLs" -Arguments $scrapeArgs
}
else {
    Write-Host ""
    Write-Host "==> Phase 1 skipped (-SkipScrape)" -ForegroundColor Yellow
}

if ($RefreshUni) {
    $uniArgs = @($DownloadScript, "--code-dir", $CodeDir, "--clean-uni-only")
    Invoke-PythonStep -Label "Refresh uni_req -> clean/uni" -Arguments $uniArgs
}

$downloadArgs = @($DownloadScript, "--code-dir", $CodeDir)
if ($downloadFresh) {
    $downloadArgs += "--fresh"
}
if ($Limit -gt 0) {
    $downloadArgs += @("--limit", $Limit)
}
if ($CleanOnly) {
    $downloadArgs += "--clean-only"
}
if ($DownloadOnly) {
    $downloadArgs += "--download-only"
}

Invoke-PythonStep -Label "Phase 2 - download + clean course pages" -Arguments $downloadArgs

Write-Host ""
Write-Host "Done. Next step (not run here):" -ForegroundColor Green
Write-Host "  python `"$RepoRoot\shared\llm_extract.py`" `"$CodeDir`""
