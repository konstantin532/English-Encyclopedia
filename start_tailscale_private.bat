@echo off
chcp 65001 >nul
title English Encyclopedia - Tailscale Private
cd /d "%~dp0"
echo.
echo === English Encyclopedia: private HTTPS via Tailscale Serve ===
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_tailscale_private.ps1"
if errorlevel 1 echo [ERROR] Private server did not start. See the message above.
echo.
pause
