@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

if not "%1"=="--silent" (
    echo ============================================
    echo  Thingswell Inc.
    echo  Multimodal Emotion Recognition ^& Korean STT Monitor
    echo  Beta Test Release v0.1.0
    echo  Copyright (c) 2026 Thingswell Inc.
    echo  Contact: hjlee@thingswell.co.kr
    echo ============================================
    echo.
    echo  [NOTE] Python 3.11 권장. Python 3.13은 미검증입니다.
    echo.
)

echo [INFO] Installing minimal (base) packages...
echo.

REM Navigate to project root
pushd "%~dp0..\.."

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Please install Python 3.11 from https://python.org
    echo         Make sure to check "Add Python to PATH" during install.
    popd
    if not "%1"=="--silent" pause
    exit /b 1
)

REM Create .venv if not exists
if not exist ".venv" (
    echo [INFO] Creating virtual environment (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        popd
        if not "%1"=="--silent" pause
        exit /b 1
    )
    echo [DONE] Virtual environment created.
)

REM Activate .venv
echo [INFO] Activating virtual environment...
call ".venv\Scripts\activate.bat"

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

REM Install minimal requirements
echo [INFO] Installing requirements-minimal.txt...
pip install -r requirements-minimal.txt
if errorlevel 1 (
    echo [ERROR] Failed to install minimal packages.
    popd
    if not "%1"=="--silent" pause
    exit /b 1
)

echo.
echo [DONE] Minimal packages installed successfully.
popd
if not "%1"=="--silent" pause
exit /b 0
