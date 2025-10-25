#!/bin/bash

# RoboDialer Docker Deployment Script
echo "🚀 Deploying RoboDialer Application..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "📝 Please copy .env.prod.example to .env and fill in your values"
    exit 1
fi

# Pull latest images
echo "📥 Pulling latest Docker images..."
docker pull ghcr.io/caprae-capital-partners/leadgenai-robodialer-backend:latest
docker pull ghcr.io/caprae-capital-partners/leadgenai-robodialer-frontend:latest

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down

# Start new containers
echo "▶️ Starting new containers..."
docker-compose -f docker-compose.prod.yml up -d

# Show status
echo "📊 Container Status:"
docker-compose -f docker-compose.prod.yml ps

echo "✅ Deployment Complete!"
echo "🌐 Frontend: http://localhost:9002"
echo "🔧 Backend: http://localhost:8001"
echo "📋 To view logs: docker-compose -f docker-compose.prod.yml logs"