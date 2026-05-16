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
echo  [NOTE] Windows 11 + Python 3.11 권장
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
set SKIP=0

echo === Required modules ===
echo.

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
echo === Optional modules (face mode) ===
echo.

REM Check deepface
python -c "import deepface" >nul 2>&1
if errorlevel 1 (
    echo [SKIP] deepface not installed (face mode disabled)
    set /a SKIP+=1
) else (
    echo [PASS] deepface installed
    set /a PASS+=1
)

REM Check tensorflow or tf_keras
python -c "import tensorflow" >nul 2>&1
if errorlevel 1 (
    python -c "import tf_keras" >nul 2>&1
    if errorlevel 1 (
        echo [SKIP] tensorflow/tf_keras not installed (face mode may use fallback)
        set /a SKIP+=1
    ) else (
        echo [PASS] tf_keras installed
        set /a PASS+=1
    )
) else (
    echo [PASS] tensorflow installed
    set /a PASS+=1
)

echo.
echo === Optional modules (voice mode) ===
echo.

REM Check sounddevice
python -c "import sounddevice" >nul 2>&1
if errorlevel 1 (
    echo [SKIP] sounddevice not installed (voice mode disabled)
    set /a SKIP+=1
) else (
    echo [PASS] sounddevice installed
    set /a PASS+=1
)

REM Check librosa
python -c "import librosa" >nul 2>&1
if errorlevel 1 (
    echo [SKIP] librosa not installed (voice mode disabled)
    set /a SKIP+=1
) else (
    echo [PASS] librosa installed
    set /a PASS+=1
)

echo.
echo === Optional modules (STT) ===
echo.

REM Check faster-whisper
python -c "import faster_whisper" >nul 2>&1
if errorlevel 1 (
    echo [SKIP] faster-whisper not installed (STT disabled)
    set /a SKIP+=1
) else (
    echo [PASS] faster-whisper installed
    set /a PASS+=1
)

echo.
echo === Device check ===
echo.

REM Camera device check
python -c "import cv2; cap=cv2.VideoCapture(0); ok=cap.isOpened(); cap.release(); print('[PASS] Camera device 0: available' if ok else '[SKIP] Camera device 0: not available')" 2>nul
if errorlevel 1 (
    echo [SKIP] Camera check failed (cv2 not available)
)

REM Microphone device check
python -c "import sounddevice as sd; devs=[d for d in sd.query_devices() if d['max_input_channels']>0]; print(f'[PASS] Microphone devices found: {len(devs)}') if devs else print('[SKIP] No microphone devices found')" 2>nul
if errorlevel 1 (
    echo [SKIP] Microphone check skipped (sounddevice not available)
)

echo.
echo === Saving pip freeze ===
echo.

REM Save pip freeze to test_report
if not exist "test_report" mkdir test_report
pip freeze > "test_report\pip_freeze.txt" 2>&1
echo [DONE] pip freeze saved to test_report\pip_freeze.txt

echo.
echo ============================================
echo  Health Check Results:
echo  PASS: %PASS%  /  FAIL: %FAIL%  /  SKIP: %SKIP%
echo ============================================
echo.
echo  [INFO] FAIL = required module missing (install needed)
echo  [INFO] SKIP = optional module (mode-specific, not blocking)
echo         minimal mode runs with streamlit + opencv + numpy only.
echo.

if %FAIL% GTR 0 (
    echo  [ACTION] Run install_all.bat or install_minimal.bat to fix FAIL items.
)

popd
echo.
pause
exit /b 0
