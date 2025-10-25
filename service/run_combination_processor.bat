@echo off
echo ========================================
echo CSV Combination API Processor
echo ========================================
echo.

REM Change to the directory where this script is located
cd /d "%~dp0"
echo Working directory: %CD%
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found
    echo Installing dependencies globally...
    pip install -r requirements_combination_processor.txt
)

echo.
echo Starting combination processor...
echo Press Ctrl+C to stop processing
echo.

python run_combination_processor.py

echo.
echo Processing completed!
pause