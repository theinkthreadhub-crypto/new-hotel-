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
