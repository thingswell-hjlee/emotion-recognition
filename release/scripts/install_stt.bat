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
    echo  [NOTE] 기본 STT 엔진: faster-whisper (Windows 호환)
    echo  [NOTE] openai-whisper는 optional입니다.
    echo.
)

echo [INFO] Installing STT (Speech-to-Text) modules...
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

pip install -r requirements-stt.txt
if errorlevel 1 (
    echo [ERROR] Failed to install STT packages.
    echo         Ensure you have Python 3.11 and C++ Build Tools.
    popd
    if not "%1"=="--silent" pause
    exit /b 1
)

echo.
echo [DONE] STT modules installed (faster-whisper).
echo [NOTE] First run will download Whisper model (~40-250MB).
echo [NOTE] openai-whisper는 별도 설치: pip install -r requirements-stt-openai-optional.txt
popd
if not "%1"=="--silent" pause
exit /b 0
