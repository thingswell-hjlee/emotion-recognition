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
echo [INFO] Collecting test logs and system information...
echo.

REM Navigate to project root
pushd "%~dp0..\.."

REM Activate .venv if exists
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

REM Create test_report directory
if not exist "test_report" mkdir test_report

REM Get current date and time
for /f "tokens=*" %%i in ('date /t') do set "CURRENT_DATE=%%i"
for /f "tokens=*" %%i in ('time /t') do set "CURRENT_TIME=%%i"
for /f "tokens=*" %%i in ('hostname') do set "PC_NAME=%%i"

REM ──────────────────────────────────────
REM Save python_version.txt
REM ──────────────────────────────────────
echo [INFO] Saving python_version.txt...
python --version > "test_report\python_version.txt" 2>&1
echo [DONE] python_version.txt

REM ──────────────────────────────────────
REM Save pip_freeze.txt
REM ──────────────────────────────────────
echo [INFO] Saving pip_freeze.txt...
pip freeze > "test_report\pip_freeze.txt" 2>&1
echo [DONE] pip_freeze.txt

REM ──────────────────────────────────────
REM Generate system_info.txt
REM ──────────────────────────────────────
echo [INFO] Generating system_info.txt...

(
    echo ============================================
    echo  Test Report - System Information
    echo ============================================
    echo.
    echo [Company Information]
    echo company: Thingswell Inc.
    echo app_name: Multimodal Emotion Recognition ^& Korean STT Monitor
    echo project_name: emotion-recognition
    echo version: 0.1.0
    echo release_channel: Beta Test Release
    echo build_tag: beta-win64-v0.1.0
    echo copyright: Copyright (c) 2026 Thingswell Inc. All rights reserved.
    echo contact_email: hjlee@thingswell.co.kr
    echo website: https://thingswell.co.kr
    echo.
    echo [Test Environment]
    echo tester_pc_name: %PC_NAME%
    echo test_date: %CURRENT_DATE%
    echo test_time: %CURRENT_TIME%
    echo.
    echo [Python Environment]
) > "test_report\system_info.txt"

python --version >> "test_report\system_info.txt" 2>&1
echo. >> "test_report\system_info.txt"

echo [OS Information] >> "test_report\system_info.txt"
systeminfo | findstr /C:"OS Name" /C:"OS Version" /C:"System Type" /C:"Total Physical Memory" >> "test_report\system_info.txt" 2>&1

echo [DONE] system_info.txt

REM ──────────────────────────────────────
REM Generate test_report_summary.json
REM ──────────────────────────────────────
echo [INFO] Generating test_report_summary.json...

python -c "import json, sys, os, platform; sys.path.insert(0, '.'); from version import *; data={'company': COMPANY_NAME, 'app_name': APP_NAME, 'project_name': PROJECT_NAME, 'version': VERSION, 'release_channel': RELEASE_CHANNEL, 'build_tag': BUILD_TAG, 'copyright': COPYRIGHT, 'contact_email': CONTACT_EMAIL, 'website': WEBSITE, 'build_date': BUILD_DATE, 'tester_pc_name': platform.node(), 'test_datetime': __import__('datetime').datetime.now().isoformat(), 'python_version': platform.python_version(), 'platform': platform.platform(), 'selected_mode': 'N/A', 'selected_profile': 'N/A'}; f=open('test_report/test_report_summary.json','w',encoding='utf-8'); json.dump(data, f, indent=2, ensure_ascii=False); f.close(); print('[DONE] test_report_summary.json')" 2>&1

if errorlevel 1 (
    echo [WARNING] Could not generate JSON report. Python or version.py may not be accessible.
)

REM ──────────────────────────────────────
REM Generate performance_metrics.csv header
REM ──────────────────────────────────────
echo [INFO] Checking performance_metrics.csv...

if not exist "test_report\performance_metrics.csv" (
    (
        echo # Thingswell Inc. - Multimodal Emotion Recognition ^& Korean STT Monitor
        echo # Version: Beta Test Release v0.1.0
        echo # Copyright (c) 2026 Thingswell Inc. All rights reserved.
        echo # PC: %PC_NAME% / Date: %CURRENT_DATE% %CURRENT_TIME%
        echo timestamp,module,metric_name,metric_value,unit,profile
    ) > "test_report\performance_metrics.csv"
    echo [DONE] performance_metrics.csv created (header only).
) else (
    echo [INFO] performance_metrics.csv already exists (preserved).
)

REM ──────────────────────────────────────
REM Generate reliability_events.csv header
REM ──────────────────────────────────────
echo [INFO] Checking reliability_events.csv...

if not exist "test_report\reliability_events.csv" (
    (
        echo # Thingswell Inc. - Multimodal Emotion Recognition ^& Korean STT Monitor
        echo # Version: Beta Test Release v0.1.0
        echo # Copyright (c) 2026 Thingswell Inc. All rights reserved.
        echo # PC: %PC_NAME% / Date: %CURRENT_DATE% %CURRENT_TIME%
        echo timestamp,event_type,module,description,severity
    ) > "test_report\reliability_events.csv"
    echo [DONE] reliability_events.csv created (header only).
) else (
    echo [INFO] reliability_events.csv already exists (preserved).
)

REM ──────────────────────────────────────
REM Copy app logs if exist
REM ──────────────────────────────────────
if exist "logs" (
    echo [INFO] Copying app logs...
    xcopy /E /I /Y "logs" "test_report\logs" >nul 2>&1
    echo [DONE] App logs copied.
) else (
    echo [INFO] No app logs directory found (normal for first run).
)

echo.
echo ============================================
echo  [DONE] Log collection complete.
echo.
echo  Output folder: test_report\
echo  Files generated:
echo    - python_version.txt
echo    - pip_freeze.txt
echo    - system_info.txt
echo    - test_report_summary.json
echo    - performance_metrics.csv
echo    - reliability_events.csv
echo    - logs\ (if app logs exist)
echo ============================================
echo.
echo  Please compress and send the test_report\ folder to:
echo  hjlee@thingswell.co.kr
echo.

popd
pause
exit /b 0
