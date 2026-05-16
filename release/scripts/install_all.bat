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
echo [INFO] Starting full installation...
echo.

echo [1/4] Installing minimal (base) packages...
call "%~dp0install_minimal.bat" --silent
echo.

echo [2/4] Installing face recognition modules...
call "%~dp0install_face.bat" --silent
echo.

echo [3/4] Installing voice recognition modules...
call "%~dp0install_voice.bat" --silent
echo.

echo [4/4] Installing STT modules...
call "%~dp0install_stt.bat" --silent
echo.

echo ============================================
echo  [DONE] All modules installed successfully.
echo  Run health_check.bat to verify installation.
echo ============================================
pause
