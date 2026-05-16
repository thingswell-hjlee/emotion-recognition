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
echo [INFO] Installing STT (Speech-to-Text) modules...
echo.

pushd "%~dp0..\.."
pip install -r requirements-stt.txt
popd

echo.
echo [DONE] STT modules installed.
echo [NOTE] First run will download Whisper model (~1-3GB).
if not "%1"=="--silent" pause
