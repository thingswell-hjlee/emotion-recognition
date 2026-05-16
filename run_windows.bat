@echo off
echo ============================================
echo  Emotion Monitor - Starting...
echo ============================================
echo.

:: 가상환경 활성화
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] 가상환경이 없습니다. setup_windows.bat을 먼저 실행하세요.
    pause
    exit /b 1
)

:: Streamlit 실행
echo 브라우저에서 http://localhost:8501 이 열립니다.
echo 종료: Ctrl+C
echo.
streamlit run ui/app.py --server.headless false

pause
