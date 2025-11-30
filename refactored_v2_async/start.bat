@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ================================================================================
echo PokerHub Database Extractor v2.0 - ASYNC Version (11x faster!)
echo ================================================================================
echo.

REM ==================== PATH SETUP ====================
set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"
set "MAIN_SCRIPT=%SCRIPT_DIR%main.py"
set "REQUIREMENTS=%SCRIPT_DIR%requirements.txt"
set "ENV_FILE=%SCRIPT_DIR%.env"
set "ENV_EXAMPLE=%SCRIPT_DIR%.env.example"

REM ==================== CHECK PYTHON ====================
echo [Step 1/4] Checking Python...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH!
    echo.
    echo Install Python 3.9+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo OK: Python %PYTHON_VERSION% found
echo.

REM ==================== CREATE/CHECK VENV ====================
echo [Step 2/4] Preparing virtual environment...

if exist "%PYTHON_EXE%" (
    echo OK: Virtual environment already exists
) else (
    echo Creating virtual environment .venv...
    python -m venv "%VENV_DIR%"
    
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    
    echo OK: Virtual environment created
    
    echo Updating pip...
    "%PYTHON_EXE%" -m pip install --upgrade pip --quiet
)
echo.

REM ==================== INSTALL DEPENDENCIES ====================
echo [Step 3/4] Installing dependencies...

if not exist "%REQUIREMENTS%" (
    echo ERROR: requirements.txt not found!
    pause
    exit /b 1
)

echo Installing packages from requirements.txt...
echo This may take 1-2 minutes on first run
echo.

"%PIP_EXE%" install -r "%REQUIREMENTS%" --quiet --disable-pip-version-check

if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    echo.
    echo Try manual installation:
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo OK: All dependencies installed
echo.

REM ==================== CHECK CONFIGURATION ====================
echo [Step 4/4] Checking configuration...

if not exist "%ENV_FILE%" (
    echo ERROR: .env file not found!
    echo.
    
    if exist "%ENV_EXAMPLE%" (
        echo Creating .env from .env.example...
        copy "%ENV_EXAMPLE%" "%ENV_FILE%" >nul
        echo OK: .env file created
        echo.
        echo IMPORTANT: Edit .env before continuing!
        echo.
        notepad "%ENV_FILE%"
        echo.
        echo Press any key after editing .env to continue...
        pause >nul
    ) else (
        echo Create .env file manually
        pause
        exit /b 1
    )
) else (
    echo OK: Configuration found
)
echo.

REM ==================== START APPLICATION ====================
echo ================================================================================
echo STARTING APPLICATION
echo ================================================================================
echo.
echo Schedule:
echo   - First update: NOW (immediately after start)
echo   - Next updates: Every 60 minutes
echo.
echo Performance:
echo   - Legacy (sync): ~330 seconds (5.5 minutes)
echo   - Current (async): ~30 seconds
echo   - Speedup: 11x FASTER!
echo.
echo Logs: pokerhub_extractor.log
echo.
echo Press Ctrl+C to stop
echo.
echo ================================================================================
echo.

REM Start Python script
"%PYTHON_EXE%" "%MAIN_SCRIPT%"

REM Handle exit
set EXIT_CODE=%errorlevel%

echo.
echo ================================================================================

if %EXIT_CODE% equ 0 (
    echo OK: Program completed successfully
) else (
    echo WARNING: Program exited with code: %EXIT_CODE%
    echo.
    echo Check log: pokerhub_extractor.log
)

echo ================================================================================
echo.
pause