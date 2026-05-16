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
echo  [NOTE] Python 3.11 권장. Python 3.13은 미검증입니다.
echo  [NOTE] 전체 설치 시 약 2-5GB 디스크 공간이 필요합니다.
echo.
echo [INFO] Starting full installation (4 steps)...
echo.

REM Step 1: Minimal (creates .venv)
echo ─────────────────────────────────────────────
echo [1/4] Installing minimal (base) packages...
echo ─────────────────────────────────────────────
call "%~dp0install_minimal.bat" --silent
if errorlevel 1 (
    echo [ERROR] Step 1 failed. Cannot continue.
    pause
    exit /b 1
)
echo [1/4] DONE
echo.

REM Step 2: Face
echo ─────────────────────────────────────────────
echo [2/4] Installing face recognition modules...
echo ─────────────────────────────────────────────
call "%~dp0install_face.bat" --silent
if errorlevel 1 (
    echo [WARNING] Step 2 failed. Face mode may not work.
    echo           Continuing with remaining steps...
)
echo [2/4] DONE
echo.

REM Step 3: Voice
echo ─────────────────────────────────────────────
echo [3/4] Installing voice recognition modules...
echo ─────────────────────────────────────────────
call "%~dp0install_voice.bat" --silent
if errorlevel 1 (
    echo [WARNING] Step 3 failed. Voice mode may not work.
    echo           Continuing with remaining steps...
)
echo [3/4] DONE
echo.

REM Step 4: STT
echo ─────────────────────────────────────────────
echo [4/4] Installing STT modules...
echo ─────────────────────────────────────────────
call "%~dp0install_stt.bat" --silent
if errorlevel 1 (
    echo [WARNING] Step 4 failed. STT may not work.
)
echo [4/4] DONE
echo.

echo ============================================
echo  [DONE] Installation complete.
echo.
echo  Next steps:
echo    1. health_check.bat  (환경 검증)
echo    2. run_app.bat       (앱 실행)
echo ============================================
pause
exit /b 0
