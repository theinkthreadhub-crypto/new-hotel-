@echo off
title Setu - LAN Server
echo Starting Setu LAN server on port 8000 (phones/tablets can connect on the same WiFi)...
cd /d "%~dp0"
python app_main.py --server
pause
