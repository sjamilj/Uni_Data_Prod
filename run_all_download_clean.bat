@echo off
setlocal
echo Batch re-clean course HTML for all universities (clean only)
echo Skips Aston, ARU, and Birmingham City University by default. Press Ctrl+C to cancel.
echo.

cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_all_download_clean.ps1" -CleanOnly -Resume
if errorlevel 1 (
    echo.
    echo Failed with exit code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Done.
pause
