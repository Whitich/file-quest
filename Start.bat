@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
%PYTHON% retro_file_explorer.py %*
if errorlevel 1 (
    echo.
    echo Could not start File Quest. Follow the setup instructions in README.md.
    pause
    exit /b 1
)
