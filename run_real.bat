@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 実APIモードで実行します。料金が発生します。
echo (.env の USE_MOCK=false と、APIキー、各社の利用上限設定が必要です)
set /p OK=続行するには yes と入力してください: 
if /i not "%OK%"=="yes" exit /b
set PYTHONPATH=%~dp0src
py -m ai_business_lab --real %*
pause
