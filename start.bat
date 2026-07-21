@echo off
chcp 65001 >nul 2>&1
title Uni-TTS

cd /d "%~dp0"

set "VENV_PYTHON=.venv\Scripts\python.exe"
set "VENV_PIP=.venv\Scripts\pip.exe"

if not exist "%VENV_PYTHON%" (
    echo [*] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [!] Failed to create venv. Please install Python 3.10+.
        pause
        exit /b 1
    )
)

echo [*] Installing Python dependencies...
"%VENV_PIP%" install -r requirements.txt -q --disable-pip-version-check

echo [*] Launching Uni-TTS...
"%VENV_PYTHON%" start.py

pause
