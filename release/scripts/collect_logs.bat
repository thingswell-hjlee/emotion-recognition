@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

echo.
echo ============================================
echo  Thingswell Inc.
echo  Multimodal Emotion Recognition ^& Korean STT Monitor
echo  Beta Test Release v0.1.0
echo  Log Collector
echo ============================================
echo.

REM ZIP 루트로 이동 (release\scripts 기준 2단계 상위)
pushd "%~dp0..\.."

REM 타임스탬프 폴더 생성
for /f "tokens=2 delims==" %%i in ('wmic os get localdatetime /value 2^>nul ^| find "="') do set "DT=%%i"
set "TS=%DT:~0,4%%DT:~4,2%%DT:~6,2%_%DT:~8,2%%DT:~10,2%%DT:~12,2%"
set "REPORT_DIR=test_report_%TS%"

if not exist "%REPORT_DIR%" mkdir "%REPORT_DIR%"

echo  출력 폴더: %REPORT_DIR%
echo.

REM ── system_info.txt ──
echo  [1/6] system_info.txt ...
(
    echo ============================================
    echo  Test Report - System Information
    echo ============================================
    echo.
    echo [Company]
    echo company: Thingswell Inc.
    echo app_name: Multimodal Emotion Recognition ^& Korean STT Monitor
    echo version: 0.1.0
    echo build_tag: beta-win64-v0.1.0
    echo copyright: Copyright (c) 2026 Thingswell Inc.
    echo contact: hjlee@thingswell.co.kr
    echo.
    echo [Environment]
    echo pc_name: %COMPUTERNAME%
    echo user: %USERNAME%
    echo date: %DATE% %TIME%
    echo.
    echo [OS]
) > "%REPORT_DIR%\system_info.txt"
systeminfo 2>nul | findstr /C:"OS Name" /C:"OS Version" /C:"System Type" /C:"Total Physical Memory" >> "%REPORT_DIR%\system_info.txt" 2>&1
echo  OK

REM ── python_version.txt ──
echo  [2/6] python_version.txt ...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" --version > "%REPORT_DIR%\python_version.txt" 2>&1
) else (
    python --version > "%REPORT_DIR%\python_version.txt" 2>&1
    if errorlevel 1 (
        echo Python not found > "%REPORT_DIR%\python_version.txt"
    )
)
echo  OK

REM ── pip_freeze.txt ──
echo  [3/6] pip_freeze.txt ...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m pip freeze > "%REPORT_DIR%\pip_freeze.txt" 2>&1
) else (
    echo .venv not found - pip freeze skipped > "%REPORT_DIR%\pip_freeze.txt"
)
echo  OK

REM ── version_info.txt (from version.py) ──
echo  [4/6] version_info.txt ...
if exist "version.py" (
    if exist ".venv\Scripts\python.exe" (
        ".venv\Scripts\python.exe" -c "import sys; sys.path.insert(0,'.'); from version import *; print(f'APP_NAME={APP_NAME}\nVERSION={VERSION}\nBUILD_TAG={BUILD_TAG}\nCOMPANY={COMPANY_NAME}\nCOPYRIGHT={COPYRIGHT}\nCONTACT={CONTACT_EMAIL}')" > "%REPORT_DIR%\version_info.txt" 2>&1
    ) else (
        type version.py > "%REPORT_DIR%\version_info.txt"
    )
) else (
    echo version.py not found > "%REPORT_DIR%\version_info.txt"
)
echo  OK

REM ── health_check.txt ──
echo  [5/6] health_check.txt ...
if exist "logs\health_check.txt" (
    copy /Y "logs\health_check.txt" "%REPORT_DIR%\health_check.txt" >nul 2>&1
    echo  OK (copied)
) else (
    echo health_check not yet run > "%REPORT_DIR%\health_check.txt"
    echo  OK (not available)
)

REM ── app logs ──
echo  [6/6] app logs ...
if exist "logs" (
    xcopy /E /I /Y "logs" "%REPORT_DIR%\logs" >nul 2>&1
    echo  OK (copied)
) else (
    echo  SKIP (no logs folder)
)

echo.
echo ============================================
echo  [DONE] 로그 수집 완료
echo.
echo  폴더: %REPORT_DIR%\
echo.
echo  이 폴더를 ZIP으로 압축하여
echo  hjlee@thingswell.co.kr 로 전달해 주세요.
echo ============================================
echo.

popd
pause
exit /b 0
