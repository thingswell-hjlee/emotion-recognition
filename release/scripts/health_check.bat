@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

echo ============================================
echo  Thingswell Inc.
echo  Multimodal Emotion Recognition ^& Korean STT Monitor
echo  Beta Test Release v0.1.0
echo  Copyright (c) 2026 Thingswell Inc.
echo  Contact: hjlee@thingswell.co.kr
echo ============================================
echo.
echo [INFO] Running environment health check...
echo.

REM Navigate to project root
pushd "%~dp0..\.."

REM Activate .venv if exists
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    echo [INFO] Virtual environment: .venv (activated)
) else (
    echo [INFO] Virtual environment: not found (using system Python)
)
echo.

set PASS=0
set FAIL=0

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Python not found
    set /a FAIL+=1
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [PASS] %%i
    set /a PASS+=1
)

REM Check pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] pip not found
    set /a FAIL+=1
) else (
    echo [PASS] pip available
    set /a PASS+=1
)

REM Check streamlit
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] streamlit not installed (required)
    set /a FAIL+=1
) else (
    echo [PASS] streamlit installed
    set /a PASS+=1
)

REM Check opencv
python -c "import cv2" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] opencv (cv2) not installed (required)
    set /a FAIL+=1
) else (
    echo [PASS] opencv (cv2) installed
    set /a PASS+=1
)

REM Check numpy
python -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] numpy not installed (required)
    set /a FAIL+=1
) else (
    echo [PASS] numpy installed
    set /a PASS+=1
)

echo.
echo --- Optional modules (face mode) ---

REM Check deepface
python -c "import deepface" >nul 2>&1
if errorlevel 1 (
    echo [SKIP] deepface not installed (face mode disabled)
    set /a FAIL+=1
) else (
    echo [PASS] deepface installed
    set /a PASS+=1
)

echo.
echo --- Optional modules (voice mode) ---

REM Check sounddevice
python -c "import sounddevice" >nul 2>&1
if errorlevel 1 (
    echo [SKIP] sounddevice not installed (voice mode disabled)
    set /a FAIL+=1
) else (
    echo [PASS] sounddevice installed
    set /a PASS+=1
)

REM Check librosa
python -c "import librosa" >nul 2>&1
if errorlevel 1 (
    echo [SKIP] librosa not installed (voice mode disabled)
    set /a FAIL+=1
) else (
    echo [PASS] librosa installed
    set /a PASS+=1
)

echo.
echo --- Optional modules (STT) ---

REM Check faster-whisper
python -c "import faster_whisper" >nul 2>&1
if errorlevel 1 (
    echo [SKIP] faster-whisper not installed (STT disabled)
    set /a FAIL+=1
) else (
    echo [PASS] faster-whisper installed
    set /a PASS+=1
)

echo.
echo ============================================
echo  Health Check Results:
echo  PASS: %PASS%  /  FAIL or SKIP: %FAIL%
echo ============================================
echo.
echo  [INFO] SKIP items are optional modules.
echo         minimal mode runs with streamlit + opencv + numpy only.

popd
echo.
pause
exit /b 0
