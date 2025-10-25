@echo off
REM RoboDialer System Startup Script for Windows
REM This script helps you start the complete RoboDialer system with ngrok

echo 🚀 Starting AI-Powered RoboDialer System...
echo.

REM Check if ngrok is installed
where ngrok >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Ngrok is not installed or not in PATH
    echo Please install ngrok first:
    echo   Windows: winget install ngrok.ngrok
    echo   Then restart your terminal
    pause
    exit /b 1
)

echo ✅ Ngrok found

REM Check if we're in the right directory
if not exist "..\..\app.py" (
    echo ❌ Please run this script from the backend_robodialer directory
    echo Expected structure: ../../app.py (main backend app)
    pause
    exit /b 1
)

echo ✅ Directory structure verified

REM Check environment files
if not exist ".env" (
    echo ❌ Backend .env file not found
    echo Please copy .env.example to .env and configure your credentials
    pause
    exit /b 1
)

if not exist "frontend\.env.local" (
    echo ❌ Frontend .env.local file not found
    echo Please copy frontend\.env.example to frontend\.env.local
    pause
    exit /b 1
)

echo ✅ Environment files found
echo.

echo 📋 Startup Instructions:
echo.
echo 1. Start Backend (Terminal 1):
echo    cd %CD%\..\..
echo    python -m venv venv
echo    venv\Scripts\activate
echo    pip install -r requirements.txt
echo    python app.py
echo.

echo 2. Start Ngrok Tunnel (Terminal 2):
echo    ngrok http 8000
echo    📝 Copy the HTTPS URL from ngrok output
echo.

echo 3. Update Environment Files with Ngrok URL:
echo    Edit .env and frontend\.env.local
echo    Set BASE_URL and NEXT_PUBLIC_BASE_URL to your ngrok URL
echo.

echo 4. Restart Backend with new URLs (Terminal 1):
echo    Ctrl+C to stop, then restart: python app.py
echo.

echo 5. Start Frontend (Terminal 3):
echo    cd %CD%\frontend
echo    npm install
echo    npm run dev
echo.

echo 6. Access Application:
echo    Frontend: http://localhost:9002
echo    Backend: http://localhost:8000
echo.

echo 🔗 Important Links:
echo    - Twilio Console: https://console.twilio.com/
echo    - Configure TwiML App with your ngrok URL
echo    - Voice URL: https://your-ngrok-url.ngrok-free.app/api/twilio/voice
echo.

echo ⚠️  Remember:
echo    - Ngrok URLs change each restart
echo    - Update .env files whenever ngrok restarts
echo    - Keep ngrok running during development
echo.

echo Ready to start! Follow the steps above in separate terminals.
pause