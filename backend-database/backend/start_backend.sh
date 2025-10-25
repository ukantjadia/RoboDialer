#!/bin/bash

echo "========================================"
echo "  🤖 RoboDialer Startup Script"
echo "========================================"
echo

# Check if we're in the right directory
if [ ! -d "services/backend_robodialer" ]; then
    echo "❌ ERROR: Please run this script from the main backend directory"
    echo "Expected location: LeadGenAI/backend-database/backend/"
    echo "Current location: $(pwd)"
    exit 1
fi

echo "✅ Starting RoboDialer Backend..."
echo

# Check if virtual environment exists
if [ ! -f "venv/bin/activate" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ ERROR: Failed to create virtual environment"
        echo "Make sure Python 3.8+ is installed"
        exit 1
    fi
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to install dependencies"
    exit 1
fi

# Check environment file
if [ ! -f ".env" ]; then
    echo "⚠️  WARNING: .env file not found"
    echo "Please copy .env.example to .env and configure your credentials"
    echo
    read -p "Press Enter to continue..."
fi

# Start the application
echo
echo "🚀 Starting Flask Backend on http://localhost:8000"
echo
echo "⚠️  IMPORTANT: Don't forget to start ngrok in another terminal:"
echo "   ngrok http 8000"
echo
echo "Press Ctrl+C to stop the server"
echo

python app.py