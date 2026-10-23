@echo off
title Setu POS - Windows Setup Installer
color 0b

echo ======================================================================
echo       AGHANYA DEVANYA ENTERPRISES - HOTEL ERP SETUP INSTALLER
echo ======================================================================
echo.
echo Installing Setu - Restaurant and Hotel POS to your PC...
echo.

set SCRIPT_DIR=%~dp0
set INSTALL_DIR=%LOCALAPPDATA%\Programs\AghanyaDevanyaERP
set SHORTCUT_NAME=Setu POS
set DESKTOP_DIR=%USERPROFILE%\Desktop
set STARTMENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Setu POS

echo [1/4] Creating installation directory at:
echo       "%INSTALL_DIR%"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%STARTMENU_DIR%" mkdir "%STARTMENU_DIR%"

echo [2/4] Copying executable files...
copy /Y "%SCRIPT_DIR%Aghanya-Devanya-Hotel-ERP.exe" "%INSTALL_DIR%\" >nul
copy /Y "%SCRIPT_DIR%hotel_erp.html" "%INSTALL_DIR%\" >nul
copy /Y "%SCRIPT_DIR%manifest.json" "%INSTALL_DIR%\" >nul
copy /Y "%SCRIPT_DIR%sw.js" "%INSTALL_DIR%\" >nul
copy /Y "%SCRIPT_DIR%icon-192.png" "%INSTALL_DIR%\" >nul
copy /Y "%SCRIPT_DIR%icon-512.png" "%INSTALL_DIR%\" >nul
copy /Y "%SCRIPT_DIR%favicon.ico" "%INSTALL_DIR%\" >nul

echo [3/4] Creating Desktop and Start Menu Shortcuts...
set VBS_FILE=%TEMP%\CreateErpShortcuts.vbs

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_FILE%"

:: Desktop Shortcut
echo sDeskLink = "%DESKTOP_DIR%\%SHORTCUT_NAME%.lnk" >> "%VBS_FILE%"
echo Set oDeskLink = oWS.CreateShortcut(sDeskLink) >> "%VBS_FILE%"
echo oDeskLink.TargetPath = "%INSTALL_DIR%\Aghanya-Devanya-Hotel-ERP.exe" >> "%VBS_FILE%"
echo oDeskLink.WorkingDirectory = "%INSTALL_DIR%" >> "%VBS_FILE%"
echo oDeskLink.Description = "Setu - Restaurant and Hotel POS (Aghanya Devanya Enterprises)" >> "%VBS_FILE%"
if exist "%INSTALL_DIR%\favicon.ico" (
    echo oDeskLink.IconLocation = "%INSTALL_DIR%\favicon.ico,0" >> "%VBS_FILE%"
)
echo oDeskLink.Save >> "%VBS_FILE%"

:: Start Menu Shortcut
echo sStartLink = "%STARTMENU_DIR%\%SHORTCUT_NAME%.lnk" >> "%VBS_FILE%"
echo Set oStartLink = oWS.CreateShortcut(sStartLink) >> "%VBS_FILE%"
echo oStartLink.TargetPath = "%INSTALL_DIR%\Aghanya-Devanya-Hotel-ERP.exe" >> "%VBS_FILE%"
echo oStartLink.WorkingDirectory = "%INSTALL_DIR%" >> "%VBS_FILE%"
echo oStartLink.Description = "Setu - Restaurant and Hotel POS (Aghanya Devanya Enterprises)" >> "%VBS_FILE%"
if exist "%INSTALL_DIR%\favicon.ico" (
    echo oStartLink.IconLocation = "%INSTALL_DIR%\favicon.ico,0" >> "%VBS_FILE%"
)
echo oStartLink.Save >> "%VBS_FILE%"

cscript //nologo "%VBS_FILE%"
del "%VBS_FILE%"

echo [4/4] Installation Complete!
echo.
echo ======================================================================
echo    SUCCESS: Setu POS has been installed on your PC!
echo.
echo    - Desktop Shortcut created: "%SHORTCUT_NAME%"
echo    - Start Menu entry created: Programs ^> Setu POS
echo    - Standalone Executable: "%INSTALL_DIR%\Aghanya-Devanya-Hotel-ERP.exe"
echo ======================================================================
echo.
set /p LAUNCH="Kya aap abhi software start karna chahte hain? (Y/N): "
if /i "%LAUNCH%"=="Y" (
    start "" "%INSTALL_DIR%\Aghanya-Devanya-Hotel-ERP.exe"
)
pause
