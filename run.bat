@echo off
REM Jalankan DanzSuperOptimizer sebagai Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
python danzsuperoptimizer.py
pause
