@echo off
chcp 65001 >nul
title AI資料まとめくん - 起動中
cls
echo ========================================
echo   AI資料まとめくん 起動中...
echo ========================================
echo.

REM VS Codeをバックグラウンドで起動
echo [1/3] VS Codeを起動しています...
start /MIN "" "code" "%~dp0"

REM 少し待機してからStreamlitを起動
timeout /t 3 /nobreak >nul

REM Streamlitアプリを起動
echo [2/3] Streamlitアプリを起動しています...
echo.
echo ブラウザで http://localhost:8501 が開きます
echo このウィンドウは閉じないでください！
echo.
cd /d "%~dp0"
streamlit run app.py --server.port 8501

echo.
echo [3/3] アプリが終了しました
pause
