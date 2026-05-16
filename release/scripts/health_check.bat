@echo off
chcp 65001 >nul 2>&1
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
    echo [FAIL] streamlit not installed
    set /a FAIL+=1
) else (
    echo [PASS] streamlit installed
    set /a PASS+=1
)

REM Check opencv
python -c "import cv2" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] opencv (cv2) not installed
    set /a FAIL+=1
) else (
    echo [PASS] opencv (cv2) installed
    set /a PASS+=1
)

REM Check deepface
python -c "import deepface" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] deepface not installed
    set /a FAIL+=1
) else (
    echo [PASS] deepface installed
    set /a PASS+=1
)

REM Check pyaudio
python -c "import pyaudio" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] pyaudio not installed
    set /a FAIL+=1
) else (
    echo [PASS] pyaudio installed
    set /a PASS+=1
)

REM Check webrtcvad
python -c "import webrtcvad" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] webrtcvad not installed
    set /a FAIL+=1
) else (
    echo [PASS] webrtcvad installed
    set /a PASS+=1
)

REM Check faster-whisper
python -c "import faster_whisper" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] faster-whisper not installed
    set /a FAIL+=1
) else (
    echo [PASS] faster-whisper installed
    set /a PASS+=1
)

REM Check torch
python -c "import torch" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] torch not installed
    set /a FAIL+=1
) else (
    echo [PASS] torch installed
    set /a PASS+=1
)

echo.
echo ============================================
echo  Health Check Results:
echo  PASS: %PASS%  /  FAIL: %FAIL%
echo ============================================

if %FAIL% GTR 0 (
    echo.
    echo [WARNING] Some modules are missing.
    echo           Run install_all.bat or individual install scripts.
)

echo.
pause
