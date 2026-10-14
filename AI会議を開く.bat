@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
start "AI Company Studio" /min py -m ai_business_lab.web_server
