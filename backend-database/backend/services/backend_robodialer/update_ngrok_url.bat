@echo off
echo ========================================
echo  RoboDialer Ngrok URL Update Script
echo ========================================
echo.
echo 1. Visit http://127.0.0.1:4040 in your browser
echo 2. Copy the complete HTTPS URL (starts with https://nonstatutory-co...)
echo 3. Paste it when prompted below
echo.
set /p ngrok_url="Enter your complete ngrok URL: "

if "%ngrok_url%"=="" (
    echo Error: No URL provided!
    pause
    exit /b 1
)

echo.
echo Updating environment files with: %ngrok_url%
echo.

REM Update backend .env file
powershell -Command "(Get-Content '.env') -replace 'https://nonstatutory-co-REPLACE-WITH-FULL-SUFFIX.ngrok-free.app', '%ngrok_url%' | Set-Content '.env'"

REM Update frontend .env.local file
powershell -Command "(Get-Content 'frontend\.env.local') -replace 'https://nonstatutory-co-REPLACE-WITH-FULL-SUFFIX.ngrok-free.app', '%ngrok_url%' | Set-Content 'frontend\.env.local'"

echo.
echo ✅ Environment files updated successfully!
echo.
echo Backend .env updated with: %ngrok_url%
echo Frontend .env.local updated with: %ngrok_url%
echo.
echo Next steps:
echo 1. Restart your backend server
echo 2. Restart your frontend server  
echo 3. Test the RoboDialer functionality
echo.
pause