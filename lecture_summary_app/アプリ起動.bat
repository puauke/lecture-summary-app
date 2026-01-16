@echo off
chcp 65001 >nul
echo ========================================
echo   🧠 AI資料まとめくん 起動中...
echo ========================================
echo.

REM VS Codeをバックグラウンドで起動
echo 📂 開発環境（VS Code）を起動しています...
start /MIN "" "code" "%~dp0"

REM 少し待機してからStreamlitを起動
timeout /t 3 /nobreak >nul

REM Streamlitアプリを起動
echo 🚀 アプリを起動しています...
echo ブラウザで http://localhost:8501 が開きます
echo.
cd /d "%~dp0"
streamlit run app.py --server.port 8501

pause
