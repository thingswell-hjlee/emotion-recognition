@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
title Thingswell - Emotion Recognition Beta v0.1.0

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║                                                      ║
echo ║   Thingswell Inc.                                    ║
echo ║   Multimodal Emotion Recognition                     ║
echo ║   ^& Korean STT Monitor                               ║
echo ║                                                      ║
echo ║   Beta Test Release v0.1.0                           ║
echo ║   Copyright (c) 2026 Thingswell Inc.                 ║
echo ║   Contact: hjlee@thingswell.co.kr                    ║
echo ║                                                      ║
echo ╚══════════════════════════════════════════════════════╝
echo.
echo  이 스크립트는 설치, 환경 검증, 앱 실행을 한 번에 수행합니다.
echo  최초 실행 시 약 5~30분이 소요될 수 있습니다.
echo.
echo  [요구사항]
echo    - Python 3.11 (필수, 3.13 미검증)
echo    - 인터넷 연결 (최초 설치 시)
echo    - 카메라/마이크 (테스트 시)
echo.
echo  내부 테스트 전용 - 외부 재배포 금지
echo.
echo ─────────────────────────────────────────────────────────
echo.

REM ══════════════════════════════════════════════════
REM  ZIP 루트로 이동 (START.bat 위치 기준)
REM ══════════════════════════════════════════════════
pushd "%~dp0"

REM ══════════════════════════════════════════════════
REM  Phase 1: Python 3.11 확인
REM ══════════════════════════════════════════════════
echo [Phase 1/5] Python 3.11 확인...
echo.

set "PYTHON_CMD="

REM 1차: py -3.11 (Windows Python Launcher)
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.11"
    goto :python_found
)

REM 2차: python --version 로 3.11 확인
python --version >nul 2>&1
if errorlevel 1 goto :python_not_found

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_FULL_VER=%%v"
for /f "tokens=1,2 delims=." %%a in ("!PY_FULL_VER!") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)

if "!PY_MAJOR!"=="3" if "!PY_MINOR!"=="11" (
    set "PYTHON_CMD=python"
    goto :python_found
)

REM Python은 있지만 3.11이 아님
echo   [WARNING] Python !PY_FULL_VER! 감지됨 (3.11이 아닙니다)
echo.
if "!PY_MINOR!"=="13" (
    echo   ╔══════════════════════════════════════════════════════╗
    echo   ║  Python 3.13은 이 프로젝트에서 미검증입니다.         ║
    echo   ║  TensorFlow/DeepFace 호환 문제가 발생할 수 있습니다. ║
    echo   ╚══════════════════════════════════════════════════════╝
    echo.
)
echo   Python 3.11 설치를 권장합니다:
echo     winget install Python.Python.3.11
echo   또는: https://www.python.org/downloads/release/python-3119/
echo.
echo   설치 후 이 창을 닫고 START.bat를 다시 실행하세요.
echo.
popd
pause
exit /b 1

:python_not_found
echo   ╔══════════════════════════════════════════════════════╗
echo   ║  [ERROR] Python을 찾을 수 없습니다.                  ║
echo   ║                                                      ║
echo   ║  Python 3.11을 설치해 주세요:                        ║
echo   ║    winget install Python.Python.3.11                  ║
echo   ║  또는:                                               ║
echo   ║    https://python.org/downloads/                      ║
echo   ║                                                      ║
echo   ║  설치 시 "Add Python to PATH" 반드시 체크!            ║
echo   ╚══════════════════════════════════════════════════════╝
echo.
echo   설치 후 이 창을 닫고 START.bat를 다시 실행하세요.
echo.
popd
pause
exit /b 1

:python_found
for /f "tokens=*" %%i in ('!PYTHON_CMD! --version 2^>^&1') do set "PY_VER_STR=%%i"
echo   OK: !PY_VER_STR! (!PYTHON_CMD!)
echo.

REM ══════════════════════════════════════════════════
REM  Phase 2: .venv 가상환경 생성/활성화
REM ══════════════════════════════════════════════════
echo [Phase 2/5] 가상환경 준비...

if not exist ".venv\Scripts\python.exe" (
    echo   .venv 생성 중...
    !PYTHON_CMD! -m venv .venv
    if errorlevel 1 (
        echo   [ERROR] .venv 생성 실패.
        echo          디스크 공간, 쓰기 권한을 확인하세요.
        echo          OneDrive 동기화 폴더가 아닌지 확인하세요.
        popd
        pause
        exit /b 1
    )
    echo   OK: .venv 생성 완료
) else (
    echo   OK: .venv 이미 존재 (재사용)
)
echo.

REM .venv python/pip 경로 설정
set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"
set "VENV_PIP=%~dp0.venv\Scripts\python.exe" -m pip

REM ══════════════════════════════════════════════════
REM  Phase 3: 패키지 설치
REM ══════════════════════════════════════════════════
echo [Phase 3/5] 패키지 설치...
echo.

REM pip 업그레이드
"%VENV_PYTHON%" -m pip install --upgrade pip >nul 2>&1

REM --- 3-1: 필수 패키지 (minimal) ---
"%VENV_PYTHON%" -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo   [3-1] 필수 패키지 설치 (Streamlit, OpenCV, NumPy)...
    "%VENV_PYTHON%" -m pip install -r requirements-minimal.txt
    if errorlevel 1 (
        echo.
        echo   [ERROR] 필수 패키지 설치 실패.
        echo          인터넷 연결을 확인하세요.
        echo          release\scripts\collect_logs.bat 을 실행 후
        echo          test_report를 개발팀에 전달해 주세요.
        popd
        pause
        exit /b 1
    )
    echo   OK: 필수 패키지 설치 완료
) else (
    echo   [3-1] 필수 패키지: 이미 설치됨 (스킵)
)
echo.

REM --- 3-2: Face 모듈 (optional) ---
"%VENV_PYTHON%" -c "import deepface" >nul 2>&1
if errorlevel 1 (
    echo   [3-2] 얼굴 인식 모듈 설치 (DeepFace)...
    "%VENV_PYTHON%" -m pip install -r requirements-face.txt >nul 2>&1
    if errorlevel 1 (
        echo         설치 실패 — face mode 비활성화 (minimal은 정상 동작)
    ) else (
        echo   OK: 얼굴 인식 모듈 설치 완료
    )
) else (
    echo   [3-2] 얼굴 인식 모듈: 이미 설치됨 (스킵)
)
echo.

REM --- 3-3: Voice 모듈 (optional) ---
"%VENV_PYTHON%" -c "import sounddevice" >nul 2>&1
if errorlevel 1 (
    echo   [3-3] 음성 분석 모듈 설치 (librosa, sounddevice)...
    "%VENV_PYTHON%" -m pip install -r requirements-voice.txt >nul 2>&1
    if errorlevel 1 (
        echo         설치 실패 — voice mode 비활성화 (minimal은 정상 동작)
    ) else (
        echo   OK: 음성 분석 모듈 설치 완료
    )
) else (
    echo   [3-3] 음성 분석 모듈: 이미 설치됨 (스킵)
)
echo.

REM --- 3-4: STT 모듈 (optional) ---
"%VENV_PYTHON%" -c "import faster_whisper" >nul 2>&1
if errorlevel 1 (
    echo   [3-4] STT 모듈 설치 (faster-whisper)...
    "%VENV_PYTHON%" -m pip install -r requirements-stt.txt >nul 2>&1
    if errorlevel 1 (
        echo         설치 실패 — STT 비활성화 (minimal은 정상 동작)
    ) else (
        echo   OK: STT 모듈 설치 완료
    )
) else (
    echo   [3-4] STT 모듈: 이미 설치됨 (스킵)
)
echo.

REM ══════════════════════════════════════════════════
REM  Phase 4: 환경 검증
REM ══════════════════════════════════════════════════
echo [Phase 4/5] 환경 검증...
echo.

set PASS=0
set FAIL=0
set SKIP=0

"%VENV_PYTHON%" -c "import streamlit" >nul 2>&1
if errorlevel 1 (echo   FAIL: streamlit & set /a FAIL+=1) else (echo   PASS: streamlit & set /a PASS+=1)

"%VENV_PYTHON%" -c "import cv2" >nul 2>&1
if errorlevel 1 (echo   FAIL: opencv & set /a FAIL+=1) else (echo   PASS: opencv & set /a PASS+=1)

"%VENV_PYTHON%" -c "import numpy" >nul 2>&1
if errorlevel 1 (echo   FAIL: numpy & set /a FAIL+=1) else (echo   PASS: numpy & set /a PASS+=1)

"%VENV_PYTHON%" -c "import deepface" >nul 2>&1
if errorlevel 1 (echo   SKIP: deepface & set /a SKIP+=1) else (echo   PASS: deepface & set /a PASS+=1)

"%VENV_PYTHON%" -c "import sounddevice" >nul 2>&1
if errorlevel 1 (echo   SKIP: sounddevice & set /a SKIP+=1) else (echo   PASS: sounddevice & set /a PASS+=1)

"%VENV_PYTHON%" -c "import faster_whisper" >nul 2>&1
if errorlevel 1 (echo   SKIP: faster-whisper & set /a SKIP+=1) else (echo   PASS: faster-whisper & set /a PASS+=1)

echo.
echo   결과: PASS=%PASS% / FAIL=%FAIL% / SKIP=%SKIP%

REM 필수 모듈 최종 확인
"%VENV_PYTHON%" -c "import streamlit; import cv2; import numpy" >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [ERROR] 필수 모듈(streamlit, cv2, numpy)이 없습니다.
    echo          release\scripts\collect_logs.bat 실행 후 개발팀에 전달하세요.
    popd
    pause
    exit /b 1
)
echo   STATUS: APP_READY (앱 실행 가능)
echo.

REM ══════════════════════════════════════════════════
REM  Phase 5: 앱 실행
REM ══════════════════════════════════════════════════
echo [Phase 5/5] 앱 실행...
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║                                                      ║
echo ║  브라우저에서 아래 주소가 자동으로 열립니다:          ║
echo ║                                                      ║
echo ║      http://localhost:8501                            ║
echo ║                                                      ║
echo ║  종료하려면 이 창에서 Ctrl+C를 누르세요.             ║
echo ║                                                      ║
echo ╚══════════════════════════════════════════════════════╝
echo.

"%VENV_PYTHON%" -m streamlit run ui/app.py --server.headless=false

echo.
echo ─────────────────────────────────────────────────────────
echo  앱이 종료되었습니다.
echo.
echo  [테스트 완료 후]
echo  release\scripts\collect_logs.bat 을 실행하여
echo  생성된 test_report 폴더를 hjlee@thingswell.co.kr 로 전달해 주세요.
echo ─────────────────────────────────────────────────────────
echo.

popd
pause
exit /b 0
