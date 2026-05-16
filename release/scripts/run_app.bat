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
echo [INFO] Starting application...
echo.

REM Navigate to project root
pushd "%~dp0..\.."

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Please install Python 3.11+ and add to PATH.
    pause
    exit /b 1
)

REM Check if streamlit is available
python -m streamlit --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Streamlit is not installed.
    echo         Run install_all.bat first.
    pause
    exit /b 1
)

echo [INFO] Launching Streamlit UI...
echo [INFO] Browser will open at http://localhost:8501
echo [INFO] Press Ctrl+C to stop the application.
echo.

python -m streamlit run ui/app.py

popd
pause
