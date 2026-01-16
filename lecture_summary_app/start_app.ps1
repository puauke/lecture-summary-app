# AI資料まとめくん - スタンドアロン起動スクリプト
# VS Code 不要で起動可能

# ディレクトリ移動
$appDir = "c:\Users\ko812\OneDrive\デスクトップ\Antigravity\要約app\lecture_summary_app"
Set-Location $appDir

Write-Host "================================" -ForegroundColor Cyan
Write-Host "🧠 AI資料まとめくん - 起動中" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Python がインストールされているか確認
$pythonCheck = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python がインストールされていません" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Python: $pythonCheck" -ForegroundColor Green

# Streamlit がインストールされているか確認
$streamlitCheck = pip show streamlit 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Streamlit をインストール中..." -ForegroundColor Yellow
    pip install streamlit --quiet
}

Write-Host "✅ 依存ライブラリはインストール済み" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 アプリを起動しています..." -ForegroundColor Cyan
Write-Host ""

# USER_AGENT を設定
$env:USER_AGENT = "lecture-summary-app/1.0"

# Streamlit をバックグラウンドで起動
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

# アプリが起動したら、ブラウザを開く
Start-Sleep -Seconds 3

$browserUrl = "http://localhost:8501"
Write-Host ""
Write-Host "✅ アプリが起動しました！" -ForegroundColor Green
Write-Host ""
Write-Host "📱 以下の URL でアクセス:" -ForegroundColor Cyan
Write-Host "  • PC:    $browserUrl"
Write-Host "  • スマホ: http://YOUR_PC_IP:8501" -ForegroundColor Yellow
Write-Host ""
Write-Host "💡 YOUR_PC_IP を確認するには PowerShell で 'ipconfig' を実行してください" -ForegroundColor Gray
Write-Host ""
