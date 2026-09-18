@echo off
REM Build jadi 1 file .exe (otomatis minta Administrator saat dibuka)
cd /d "%~dp0"
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --uac-admin ^
    --name "DANZ Optimizer" ^
    --hidden-import psutil ^
    app.py
echo.
echo Selesai. File ada di: dist\DANZ Optimizer.exe
pause
