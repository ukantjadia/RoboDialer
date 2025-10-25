@echo off
echo ========================================
echo  🤖 RoboDialer Startup Script
echo ========================================
echo.

:: Check if we're in the right directory
if not exist "services\backend_robodialer" (
    echo ❌ ERROR: Please run this script from the main backend directory
    echo Expected location: LeadGenAI\backend-database\backend\
    echo Current location: %CD%
    pause
    exit /b 1
)

echo ✅ Starting RoboDialer Backend...
echo.

:: Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ ERROR: Failed to create virtual environment
        echo Make sure Python 3.8+ is installed
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

:: Install dependencies
echo 📚 Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ ERROR: Failed to install dependencies
    pause
    exit /b 1
)

:: Check environment file
if not exist ".env" (
    echo ⚠️  WARNING: .env file not found
    echo Please copy .env.example to .env and configure your credentials
    echo.
    pause
)

:: Start the application
echo.
echo 🚀 Starting Flask Backend on http://localhost:8000
echo.
echo ⚠️  IMPORTANT: Don't forget to start ngrok in another terminal:
echo    ngrok http 8000
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py
pause