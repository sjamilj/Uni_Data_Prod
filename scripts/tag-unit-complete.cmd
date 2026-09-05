@echo off
setlocal

cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tag-unit-complete.ps1" %*
exit /b %ERRORLEVEL%
