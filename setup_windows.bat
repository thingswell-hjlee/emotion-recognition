@echo off
echo ============================================
echo  Emotion Monitor - Windows Setup
echo ============================================
echo.

:: 가상환경 생성
echo [1/3] 가상환경 생성 중...
python -m venv .venv
if errorlevel 1 (
    echo [ERROR] Python을 찾을 수 없습니다. Python 3.11을 설치하세요.
    pause
    exit /b 1
)

:: 가상환경 활성화
echo [2/3] 가상환경 활성화...
call .venv\Scripts\activate.bat

:: pip 업그레이드 + 최소 패키지 설치
echo [3/3] 패키지 설치 중 (minimal mode)...
python -m pip install --upgrade pip
pip install -r requirements-minimal.txt

echo.
echo ============================================
echo  설치 완료!
echo  실행: run_windows.bat
echo ============================================
pause
