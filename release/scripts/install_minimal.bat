@echo off
chcp 65001 >nul 2>&1
if not "%1"=="--silent" (
    echo ============================================
    echo  Thingswell Inc.
    echo  Multimodal Emotion Recognition ^& Korean STT Monitor
    echo  Beta Test Release v0.1.0
    echo  Copyright (c) 2026 Thingswell Inc.
    echo  Contact: hjlee@thingswell.co.kr
    echo ============================================
    echo.
)
echo [INFO] Installing minimal (base) packages...
echo.

pushd "%~dp0..\.."
pip install --upgrade pip
pip install -r requirements-minimal.txt
popd

echo.
echo [DONE] Minimal packages installed.
if not "%1"=="--silent" pause
