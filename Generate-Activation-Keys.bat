@echo off
title Setu - License Key Generator (Aghanya Devanya Enterprises)
color 0b
cd /d "%~dp0"
echo ===================================================================
echo     SETU LICENSE KEY GENERATOR - Aghanya Devanya Enterprises
echo ===================================================================
echo.
echo Ask the client for their Install ID (shown on the Setu Sign Up / License screen).
echo Plans: 1m 2m 3m 6m 1y life demo1h demo24h   reset = owner password bhool gaya
echo.
if not exist "setu-license-private.pem" (
  echo [ERROR] setu-license-private.pem was not found in this folder.
  echo This file is kept by the vendor only. Keys cannot be generated without it.
  goto end
)
python keygen.py
:end
echo.
echo Press any key to exit...
pause >nul
