@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
py -m ai_business_lab %*
pause
