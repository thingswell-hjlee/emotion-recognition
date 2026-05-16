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
echo  최초 실행 시 약 5~15분이 소요될 수 있습니다.
echo.
echo  [요구사항]
echo    - Python 3.11 (필수)
echo    - 인터넷 연결 (최초 설치 시)
echo    - 카메라/마이크 (테스트 시)
echo.
echo  ⚠️ 내부 테스트 전용 - 외부 재배포 금지
echo.
echo ─────────────────────────────────────────────────────────
echo.

REM ══════════════════════════════════════════════════
REM  프로젝트 루트로 이동
REM ══════════════════════════════════════════════════
pushd "%~dp0"

REM ══════════════════════════════════════════════════
REM  Phase 1: Python 확인
REM ══════════════════════════════════════════════════
echo [Phase 1/5] Python 확인...

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ╔══════════════════════════════════════════════════════╗
    echo ║  [ERROR] Python을 찾을 수 없습니다.                 ║
    echo ║                                                      ║
    echo ║  Python 3.11을 설치해 주세요:                        ║
    echo ║  https://python.org/downloads/                       ║
    echo ║                                                      ║
    echo ║  설치 시 반드시 "Add Python to PATH" 체크!           ║
    echo ╚══════════════════════════════════════════════════════╝
    echo.
    popd
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PY_VER=%%i"
echo   ✓ %PY_VER% 감지됨

REM Python 3.11 권장 안내
python -c "import sys; exit(0 if sys.version_info[:2]==(3,11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo   ⚠️ Python 3.11 권장 (현재 다른 버전). 일부 기능에 문제가 있을 수 있습니다.
)
echo.

REM ══════════════════════════════════════════════════
REM  Phase 2: 가상환경 (.venv) 생성/활성화
REM ══════════════════════════════════════════════════
echo [Phase 2/5] 가상환경 준비...

if not exist ".venv\Scripts\activate.bat" (
    echo   가상환경 생성 중 (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo   [ERROR] 가상환경 생성 실패. 디스크 공간과 권한을 확인하세요.
        popd
        pause
        exit /b 1
    )
    echo   ✓ .venv 생성 완료
) else (
    echo   ✓ .venv 이미 존재 (재사용)
)

call ".venv\Scripts\activate.bat"
echo   ✓ 가상환경 활성화됨
echo.

REM ══════════════════════════════════════════════════
REM  Phase 3: 패키지 설치
REM ══════════════════════════════════════════════════
echo [Phase 3/5] 패키지 설치...
echo.

REM pip 업그레이드
python -m pip install --upgrade pip >nul 2>&1

REM 설치 여부 확인 (streamlit이 이미 있으면 스킵 가능)
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo   [3-1] 기본 패키지 설치 (Streamlit, OpenCV, NumPy)...
    pip install -r requirements-minimal.txt
    if errorlevel 1 (
        echo   [ERROR] 기본 패키지 설치 실패.
        echo          인터넷 연결과 Python 버전을 확인하세요.
        popd
        pause
        exit /b 1
    )
    echo   ✓ 기본 패키지 설치 완료
    echo.
) else (
    echo   ✓ 기본 패키지 이미 설치됨 (스킵)
    echo.
)

REM Face 모듈
python -c "import deepface" >nul 2>&1
if errorlevel 1 (
    echo   [3-2] 얼굴 인식 모듈 설치 (DeepFace)...
    pip install -r requirements-face.txt >nul 2>&1
    if errorlevel 1 (
        echo   ⚠️ 얼굴 인식 모듈 설치 실패 (face mode 비활성화, 계속 진행)
    ) else (
        echo   ✓ 얼굴 인식 모듈 설치 완료
    )
    echo.
) else (
    echo   ✓ 얼굴 인식 모듈 이미 설치됨 (스킵)
    echo.
)

REM Voice 모듈
python -c "import sounddevice" >nul 2>&1
if errorlevel 1 (
    echo   [3-3] 음성 분석 모듈 설치 (librosa, sounddevice)...
    pip install -r requirements-voice.txt >nul 2>&1
    if errorlevel 1 (
        echo   ⚠️ 음성 분석 모듈 설치 실패 (voice mode 비활성화, 계속 진행)
    ) else (
        echo   ✓ 음성 분석 모듈 설치 완료
    )
    echo.
) else (
    echo   ✓ 음성 분석 모듈 이미 설치됨 (스킵)
    echo.
)

REM STT 모듈
python -c "import faster_whisper" >nul 2>&1
if errorlevel 1 (
    echo   [3-4] STT 모듈 설치 (faster-whisper)...
    pip install -r requirements-stt.txt >nul 2>&1
    if errorlevel 1 (
        echo   ⚠️ STT 모듈 설치 실패 (STT 비활성화, 계속 진행)
    ) else (
        echo   ✓ STT 모듈 설치 완료
    )
    echo.
) else (
    echo   ✓ STT 모듈 이미 설치됨 (스킵)
    echo.
)

REM ══════════════════════════════════════════════════
REM  Phase 4: 환경 검증
REM ══════════════════════════════════════════════════
echo [Phase 4/5] 환경 검증...
echo.

set PASS=0
set TOTAL=0

python -c "import streamlit" >nul 2>&1
set /a TOTAL+=1
if errorlevel 1 (echo   ✗ streamlit) else (echo   ✓ streamlit & set /a PASS+=1)

python -c "import cv2" >nul 2>&1
set /a TOTAL+=1
if errorlevel 1 (echo   ✗ opencv) else (echo   ✓ opencv & set /a PASS+=1)

python -c "import numpy" >nul 2>&1
set /a TOTAL+=1
if errorlevel 1 (echo   ✗ numpy) else (echo   ✓ numpy & set /a PASS+=1)

python -c "import deepface" >nul 2>&1
set /a TOTAL+=1
if errorlevel 1 (echo   - deepface (optional)) else (echo   ✓ deepface & set /a PASS+=1)

python -c "import sounddevice" >nul 2>&1
set /a TOTAL+=1
if errorlevel 1 (echo   - sounddevice (optional)) else (echo   ✓ sounddevice & set /a PASS+=1)

python -c "import faster_whisper" >nul 2>&1
set /a TOTAL+=1
if errorlevel 1 (echo   - faster-whisper (optional)) else (echo   ✓ faster-whisper & set /a PASS+=1)

echo.
echo   결과: %PASS%/%TOTAL% 모듈 준비됨

REM 필수 모듈 검증
python -c "import streamlit; import cv2; import numpy" >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [ERROR] 필수 모듈(streamlit, cv2, numpy) 설치 실패.
    echo          install_all.bat을 수동 실행하거나 로그를 확인하세요.
    popd
    pause
    exit /b 1
)
echo   ✓ 필수 모듈 정상 — 앱 실행 가능
echo.

REM ══════════════════════════════════════════════════
REM  Phase 5: 앱 실행
REM ══════════════════════════════════════════════════
echo [Phase 5/5] 앱 실행...
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║                                                      ║
echo ║  브라우저에서 아래 주소가 열립니다:                   ║
echo ║                                                      ║
echo ║      http://localhost:8501                            ║
echo ║                                                      ║
echo ║  종료하려면 이 창에서 Ctrl+C를 누르세요.             ║
echo ║                                                      ║
echo ╚══════════════════════════════════════════════════════╝
echo.

python -m streamlit run ui/app.py --server.headless=false

echo.
echo ─────────────────────────────────────────────────────────
echo  앱이 종료되었습니다.
echo.
echo  [테스트 완료 후]
echo  release\scripts\collect_logs.bat 을 실행하여
echo  test_report 폴더를 hjlee@thingswell.co.kr 로 전달해 주세요.
echo ─────────────────────────────────────────────────────────
echo.

popd
pause
exit /b 0
