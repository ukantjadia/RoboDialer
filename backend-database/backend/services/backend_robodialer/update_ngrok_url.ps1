# RoboDialer Ngrok URL Update Script
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " RoboDialer Ngrok URL Update Script" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Try to get ngrok URL automatically first
Write-Host "Attempting to get ngrok URL automatically..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:4040/api/tunnels" -UseBasicParsing -TimeoutSec 5
    $data = $response.Content | ConvertFrom-Json
    $ngrok_url = $data.tunnels[0].public_url
    
    if ($ngrok_url) {
        Write-Host "✅ Found ngrok URL automatically: $ngrok_url" -ForegroundColor Green
        $use_auto = Read-Host "Use this URL? (y/n)"
        if ($use_auto -eq 'y' -or $use_auto -eq 'Y') {
            $final_url = $ngrok_url
        }
    }
} catch {
    Write-Host "❌ Could not get ngrok URL automatically" -ForegroundColor Red
}

# Manual input if auto-detection failed or user declined
if (-not $final_url) {
    Write-Host ""
    Write-Host "Manual URL entry required:" -ForegroundColor Yellow
    Write-Host "1. Visit http://127.0.0.1:4040 in your browser" 
    Write-Host "2. Copy the complete HTTPS URL (starts with https://...)"
    Write-Host "3. Paste it below"
    Write-Host ""
    $manual_url = Read-Host "Enter your complete ngrok URL"
    
    if (-not $manual_url) {
        Write-Host "Error: No URL provided!" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    $final_url = $manual_url
}

Write-Host ""
Write-Host "Updating environment files with: $final_url" -ForegroundColor Green
Write-Host ""

try {
    # Update backend .env file
    $envContent = Get-Content '.env' -Raw
    $envContent = $envContent -replace 'https://nonstatutory-co-REPLACE-WITH-FULL-SUFFIX\.ngrok-free\.app', $final_url
    $envContent | Set-Content '.env'
    Write-Host "✅ Backend .env updated" -ForegroundColor Green

    # Update frontend .env.local file  
    $frontendEnvContent = Get-Content 'frontend\.env.local' -Raw
    $frontendEnvContent = $frontendEnvContent -replace 'https://nonstatutory-co-REPLACE-WITH-FULL-SUFFIX\.ngrok-free\.app', $final_url
    $frontendEnvContent | Set-Content 'frontend\.env.local'
    Write-Host "✅ Frontend .env.local updated" -ForegroundColor Green

    Write-Host ""
    Write-Host "🎉 Environment files updated successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Updated URLs in:" -ForegroundColor Cyan
    Write-Host "  • Backend: .env" 
    Write-Host "  • Frontend: frontend\.env.local"
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Restart your backend server"
    Write-Host "2. Restart your frontend server"
    Write-Host "3. Test the RoboDialer functionality"
    
} catch {
    Write-Host "❌ Error updating files: $_" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to exit"