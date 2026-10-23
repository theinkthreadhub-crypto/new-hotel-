@echo off
title Build Aghanya Devanya Hotel ERP - Executable Generator
color 0a

echo ======================================================================
echo    AGHANYA DEVANYA ENTERPRISES - AUTOMATED EXE REBUILD SYSTEM
echo ======================================================================
echo.
echo Compiling updated software into Aghanya-Devanya-Hotel-ERP.exe...
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python nahi mila. python.org se Python 3 install karein
    echo         aur "Add python.exe to PATH" tick karein.
    pause
    exit /b 1
)

echo Installing build tools (PyInstaller, pywebview)...
python -m pip install --upgrade pyinstaller pywebview
echo.

python -m PyInstaller --noconfirm --onefile --windowed --icon "favicon.ico" --name "Aghanya-Devanya-Hotel-ERP" --add-data "hotel_erp.html;." --add-data "manifest.json;." --add-data "sw.js;." --add-data "icon-192.png;." --add-data "icon-512.png;." --add-data "logo.png;." --add-data "favicon.ico;." app_main.py

if exist "dist\Aghanya-Devanya-Hotel-ERP.exe" (
    copy /Y "dist\Aghanya-Devanya-Hotel-ERP.exe" "Aghanya-Devanya-Hotel-ERP.exe" >nul
    echo.
    echo ======================================================================
    echo    SUCCESS: The new .EXE file has been built.
    echo    Path: "%~dp0Aghanya-Devanya-Hotel-ERP.exe"
    echo ======================================================================
) else (
    echo.
    echo [ERROR] Build failed. Please check the output above.
)

echo.
pause
