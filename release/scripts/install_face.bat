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

echo [INFO] Installing face recognition modules...
echo.

REM Navigate to project root
pushd "%~dp0..\.."

REM Activate .venv if exists
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo [WARNING] .venv not found. Run install_minimal.bat first.
    echo           Continuing with system Python...
)

pip install -r requirements-face.txt
if errorlevel 1 (
    echo [ERROR] Failed to install face recognition packages.
    echo         DeepFace requires TensorFlow which needs Python 3.11.
    popd
    if not "%1"=="--silent" pause
    exit /b 1
)

echo.
echo [DONE] Face recognition modules installed.
popd
if not "%1"=="--silent" pause
exit /b 0
