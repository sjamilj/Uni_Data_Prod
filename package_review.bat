@echo off
setlocal

cd /d "%~dp0"

set "PY=python"
where python >nul 2>&1
if errorlevel 1 (
    set "PY=py -3"
)

%PY% shared\package_review_output.py %*
exit /b %ERRORLEVEL%
