<#
.SYNOPSIS
    Finds every "ENV.MD" file under a base folder (e.g. one per university's
    "code" folder) and copies it to a ".env" file in the same folder.

.DESCRIPTION
    Structure expected:
        <BasePath>\<University Name>\code\ENV.MD

    For each ENV.MD found, this creates/overwrites:
        <BasePath>\<University Name>\code\.env

.PARAMETER BasePath
    Root folder to search recursively. Defaults to the Uni_Data_Prod folder.

.PARAMETER Force
    Overwrite .env if it already exists. Without this switch, existing
    .env files are skipped (and reported).

.EXAMPLE
    .\Create-EnvFiles.ps1

.EXAMPLE
    .\Create-EnvFiles.ps1 -BasePath "D:\DATA SCOL\output\UK_Uni_Data" -Force
#>

param(
    [string]$BasePath = "D:\DATA SCOL\output\UK_Uni_Data",
    [switch]$Force
)

if (-not (Test-Path -LiteralPath $BasePath)) {
    Write-Error "Base path not found: $BasePath"
    exit 1
}

Write-Host "Searching for ENV.MD files under:`n  $BasePath`n" -ForegroundColor Cyan

# Recursively find every ENV.MD (case-insensitive by default on Windows)
$envMdFiles = Get-ChildItem -LiteralPath $BasePath -Recurse -Filter "ENV.MD" -File -ErrorAction SilentlyContinue

if (-not $envMdFiles -or $envMdFiles.Count -eq 0) {
    Write-Warning "No ENV.MD files found under $BasePath"
    exit 0
}

$created  = 0
$skipped  = 0
$overwritten = 0
$failed   = 0

foreach ($file in $envMdFiles) {
    $targetPath = Join-Path -Path $file.DirectoryName -ChildPath ".env"
    $uniFolder  = Split-Path (Split-Path $file.DirectoryName -Parent) -Leaf

    try {
        if ((Test-Path -LiteralPath $targetPath) -and -not $Force) {
            Write-Host "[SKIP] $uniFolder -> .env already exists (use -Force to overwrite)" -ForegroundColor Yellow
            $skipped++
            continue
        }

        $alreadyExisted = Test-Path -LiteralPath $targetPath

        Copy-Item -LiteralPath $file.FullName -Destination $targetPath -Force

        if ($alreadyExisted) {
            Write-Host "[OVERWRITE] $uniFolder -> .env" -ForegroundColor Magenta
            $overwritten++
        } else {
            Write-Host "[CREATED]   $uniFolder -> .env" -ForegroundColor Green
            $created++
        }
    }
    catch {
        Write-Host "[FAILED]    $uniFolder -> $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
}

Write-Host "`n---- Summary ----" -ForegroundColor Cyan
Write-Host "Total ENV.MD found : $($envMdFiles.Count)"
Write-Host "Created             : $created"
Write-Host "Overwritten         : $overwritten"
Write-Host "Skipped (existing)  : $skipped"
Write-Host "Failed              : $failed"