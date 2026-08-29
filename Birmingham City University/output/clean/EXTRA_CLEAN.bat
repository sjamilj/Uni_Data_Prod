@echo off
setlocal
echo Birmingham City University - manual extra clean (not in pipeline)
echo Applies folder-specific rules to output\clean\courses\{level}\*.md
echo.

cd /d "%~dp0..\..\.."

set "PY=python"
where python >nul 2>&1
if errorlevel 1 set "PY=py -3"

%PY% shared/extra_clean_courses.py --code-dir "Birmingham City University\code" --passes 2 %*
if errorlevel 1 (
    echo.
    echo Failed with exit code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Done.
pause
