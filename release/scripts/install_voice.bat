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
echo [INFO] Installing voice recognition modules...
echo.

pushd "%~dp0..\.."
pip install -r requirements-voice.txt
popd

echo.
echo [DONE] Voice recognition modules installed.
if not "%1"=="--silent" pause
