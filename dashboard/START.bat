@echo off
setlocal
echo University Data Pipeline Dashboard
echo ================================
echo.

cd /d "%~dp0"

set "PY=python"
where python >nul 2>&1
if errorlevel 1 (
    set "PY=py -3"
)

%PY% -c "import PySide6" 2>nul
if errorlevel 1 (
    echo PySide6 not installed. Installing now...
    echo.
    %PY% -m pip install -r "%~dp0requirements.txt"
    echo.
    if errorlevel 1 (
        echo Installation failed. Run: python -m pip install PySide6
        pause
        exit /b 1
    )
)

echo Starting dashboard...
echo.
%PY% main.py
if errorlevel 1 pause
