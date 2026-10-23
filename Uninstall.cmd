@echo off
rem (chcp 65001 removed: breaks PowerShell console output on Windows 7/8.1, error 0x1F)
rem Double-click: asks for administrator rights (click Yes), then runs uninstall.ps1.
rem Dvoynoy shchelchok: zaprosit prava administratora (nazhmite "Da"), zatem zapustit uninstall.ps1.
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator rights... / Zapros prav administratora...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"
echo.
pause
