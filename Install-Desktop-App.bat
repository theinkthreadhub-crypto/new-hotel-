@echo off
title Install Aghanya Devanya Hotel ERP Desktop App
color 0b

echo ========================================================
echo    AGHANYA DEVANYA ENTERPRISES - HOTEL ERP DESKTOP SETUP
echo ========================================================
echo.
echo Installing Desktop Shortcut for Standalone Application Mode...
echo.

set SCRIPT_DIR=%~dp0
set TARGET_URL=http://localhost:8000/hotel_erp.html
set SHORTCUT_NAME=Hotel ERP - Aghanya Devanya
set DESKTOP_DIR=%USERPROFILE%\Desktop

set VBS_FILE=%TEMP%\CreateErpShortcut.vbs

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_FILE%"
echo sLinkFile = "%DESKTOP_DIR%\%SHORTCUT_NAME%.lnk" >> "%VBS_FILE%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_FILE%"

if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
    echo oLink.TargetPath = "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" >> "%VBS_FILE%"
    echo oLink.Arguments = "--app=%TARGET_URL% --app-id=aghanya_devanya_erp" >> "%VBS_FILE%"
) else if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
    echo oLink.TargetPath = "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" >> "%VBS_FILE%"
    echo oLink.Arguments = "--app=%TARGET_URL% --app-id=aghanya_devanya_erp" >> "%VBS_FILE%"
) else if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    echo oLink.TargetPath = "%ProgramFiles%\Google\Chrome\Application\chrome.exe" >> "%VBS_FILE%"
    echo oLink.Arguments = "--app=%TARGET_URL% --app-id=aghanya_devanya_erp" >> "%VBS_FILE%"
) else (
    echo oLink.TargetPath = "%TARGET_URL%" >> "%VBS_FILE%"
)

echo oLink.Description = "Aghanya Devanya Restaurant and Hotel ERP POS" >> "%VBS_FILE%"
echo oLink.WorkingDirectory = "%SCRIPT_DIR%" >> "%VBS_FILE%"
if exist "%SCRIPT_DIR%favicon.ico" (
    echo oLink.IconLocation = "%SCRIPT_DIR%favicon.ico,0" >> "%VBS_FILE%"
)
echo oLink.Save >> "%VBS_FILE%"

cscript //nologo "%VBS_FILE%"
del "%VBS_FILE%"

echo.
echo [OK] Shortcut created successfully on your Desktop!
echo      Name: "%SHORTCUT_NAME%"
echo.
echo Aap apne desktop pe bane icon "Hotel ERP - Aghanya Devanya" pe
echo double-click karke direct standalone app chala sakte hain.
echo.
pause
