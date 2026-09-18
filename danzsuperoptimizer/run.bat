@echo off
REM Jalankan DANZ OPTIMIZER sebagai Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
python app.py
pause
