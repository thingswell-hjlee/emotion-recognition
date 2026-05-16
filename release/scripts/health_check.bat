@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

echo.
echo ============================================
echo  Thingswell Inc.
echo  Multimodal Emotion Recognition ^& Korean STT Monitor
echo  Beta Test Release v0.1.0
echo  Health Check
echo ============================================
echo.

REM ZIP 루트로 이동 (release\scripts 기준 2단계 상위)
pushd "%~dp0..\.."

REM logs 폴더 생성
if not exist "logs" mkdir "logs"

REM ── .venv 확인 ──
if not exist ".venv\Scripts\python.exe" (
    echo  [ERROR] .venv가 없습니다.
    echo          START.bat를 먼저 실행하세요.
    echo.
    echo  STATUS: NOT_READY
    (echo STATUS: NOT_READY - .venv not found) > "logs\health_check.txt"
    popd
    pause
    exit /b 1
)

set "PY=.venv\Scripts\python.exe"
echo  Python: & "%PY%" --version 2>&1
echo.

REM ── 검사 시작 ──
set PASS=0
set FAIL=0
set SKIP=0

echo  === 필수 모듈 (Required) ===

"%PY%" -c "import streamlit" >nul 2>&1
if errorlevel 1 (echo   FAIL  streamlit & set /a FAIL+=1) else (echo   PASS  streamlit & set /a PASS+=1)

"%PY%" -c "import cv2" >nul 2>&1
if errorlevel 1 (echo   FAIL  opencv & set /a FAIL+=1) else (echo   PASS  opencv & set /a PASS+=1)

"%PY%" -c "import numpy" >nul 2>&1
if errorlevel 1 (echo   FAIL  numpy & set /a FAIL+=1) else (echo   PASS  numpy & set /a PASS+=1)

echo.
echo  === 옵션 모듈 (Optional) ===

"%PY%" -c "import deepface" >nul 2>&1
if errorlevel 1 (echo   SKIP  deepface & set /a SKIP+=1) else (echo   PASS  deepface & set /a PASS+=1)

"%PY%" -c "import tf_keras" >nul 2>&1
if not errorlevel 1 (
    echo   PASS  tf_keras
    set /a PASS+=1
) else (
    "%PY%" -c "import tensorflow" >nul 2>&1
    if not errorlevel 1 (
        echo   PASS  tensorflow
        set /a PASS+=1
    ) else (
        echo   SKIP  tensorflow/tf_keras
        set /a SKIP+=1
    )
)

"%PY%" -c "import sounddevice" >nul 2>&1
if errorlevel 1 (echo   SKIP  sounddevice & set /a SKIP+=1) else (echo   PASS  sounddevice & set /a PASS+=1)

"%PY%" -c "import librosa" >nul 2>&1
if errorlevel 1 (echo   SKIP  librosa & set /a SKIP+=1) else (echo   PASS  librosa & set /a PASS+=1)

"%PY%" -c "import faster_whisper" >nul 2>&1
if errorlevel 1 (echo   SKIP  faster_whisper & set /a SKIP+=1) else (echo   PASS  faster_whisper & set /a PASS+=1)

echo.
echo  ────────────────────────────────────
echo   PASS: %PASS%  FAIL: %FAIL%  SKIP: %SKIP%
echo  ────────────────────────────────────

REM ── STATUS 판정 ──
set "STATUS=NOT_READY"
if %FAIL%==0 (
    if %SKIP%==0 (
        set "STATUS=APP_READY"
    ) else (
        set "STATUS=PARTIAL_READY"
    )
)

echo.
echo   STATUS: !STATUS!

if "!STATUS!"=="APP_READY" (
    echo   → 모든 모듈 정상. full mode 사용 가능.
)
if "!STATUS!"=="PARTIAL_READY" (
    echo   → 필수 모듈 정상. minimal mode 사용 가능.
    echo   → 일부 옵션 모듈 미설치 (face/voice/STT 일부 비활성).
)
if "!STATUS!"=="NOT_READY" (
    echo   → 필수 모듈 누락. START.bat를 다시 실행하세요.
)

REM ── 결과 파일 저장 ──
(
    echo Health Check Results
    echo ─────────────────────
    echo Date: %DATE% %TIME%
    echo Python: & "%PY%" --version 2>&1
    echo.
    echo PASS: %PASS%  FAIL: %FAIL%  SKIP: %SKIP%
    echo STATUS: !STATUS!
    echo.
    echo [필수] streamlit, cv2, numpy
    echo [옵션] deepface, tf_keras, sounddevice, librosa, faster_whisper
) > "logs\health_check.txt"

echo.
echo   결과 저장: logs\health_check.txt
echo.

popd
pause
exit /b 0
