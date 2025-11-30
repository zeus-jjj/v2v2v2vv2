@echo off
chcp 65001 >nul

set "LOG_FILE=%~dp0pokerhub_extractor.log"

cls
echo ================================================================================
echo PokerHub Database Extractor v2.0 - Live Log Monitor
echo ================================================================================
echo.

if not exist "%LOG_FILE%" (
    echo Creating empty log file...
    type nul > "%LOG_FILE%"
)

echo Live log monitoring
echo Press Ctrl+C to exit
echo.
echo ================================================================================
echo.

REM Use PowerShell for tail -f
powershell -Command "& {Get-Content '%LOG_FILE%' -Wait -Tail 30}"