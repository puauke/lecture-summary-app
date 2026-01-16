@echo off
chcp 65001 > nul

REM AI料まとめくん - Windows batch startup script

echo.
echo ================================
echo AI料まとめくん - startup
echo ================================
echo.

REM Move to the correct directory
cd /d "%~dp0"

REM Confirm path
echo Current directory: %cd%
echo.

REM Set USER_AGENT
set USER_AGENT=lecture-summary-app/1.0

REM Start Streamlit
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

pause
