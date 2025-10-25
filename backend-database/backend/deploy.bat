@echo off
REM RoboDialer Docker Deployment Script for Windows

echo 🚀 Deploying RoboDialer Application...

REM Check if .env file exists
if not exist ".env" (
    echo ❌ .env file not found!
    echo 📝 Please copy .env.prod.example to .env and fill in your values
    pause
    exit /b 1
)

REM Pull latest images
echo 📥 Pulling latest Docker images...
docker pull ghcr.io/caprae-capital-partners/leadgenai-robodialer-backend:latest
docker pull ghcr.io/caprae-capital-partners/leadgenai-robodialer-frontend:latest

REM Stop existing containers
echo 🛑 Stopping existing containers...
docker-compose -f docker-compose.prod.yml down

REM Start new containers
echo ▶️ Starting new containers...
docker-compose -f docker-compose.prod.yml up -d

REM Show status
echo 📊 Container Status:
docker-compose -f docker-compose.prod.yml ps

echo ✅ Deployment Complete!
echo 🌐 Frontend: http://localhost:9002
echo 🔧 Backend: http://localhost:8001
echo 📋 To view logs: docker-compose -f docker-compose.prod.yml logs

pause