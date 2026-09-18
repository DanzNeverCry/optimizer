@echo off
REM Build DanzSuperOptimizer jadi satu file .exe siap jual/distribusi.
REM Jalankan file ini di WINDOWS (bukan di sini). Hasil: dist\DanzSuperOptimizer.exe
cd /d "%~dp0"
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --uac-admin ^
    --name "DanzSuperOptimizer" ^
    --hidden-import psutil ^
    danzsuperoptimizer.py
echo.
echo Selesai. File ada di: dist\DanzSuperOptimizer.exe
pause
