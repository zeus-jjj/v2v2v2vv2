@echo off
chcp 65001 >nul

set "LOG_FILE=%~dp0pokerhub_extractor.log"

cls
echo ================================================================================
echo PokerHub Database Extractor v2.0 - Logs
echo ================================================================================
echo.

if not exist "%LOG_FILE%" (
    echo WARNING: Log file not found: pokerhub_extractor.log
    echo Application has not been started yet.
    echo.
    pause
    exit /b 1
)

echo Last 50 lines of log:
echo ================================================================================
echo.

type "%LOG_FILE%" | more /E +0

echo.
echo ================================================================================
echo.
echo Full path: %LOG_FILE%
echo.

choice /C YN /M "Open full log in Notepad?"

if %errorlevel% equ 1 (
    notepad "%LOG_FILE%"
)