#!/bin/bash
# Render.com start script for Next.js application

echo "Starting Next.js application..."

# Use the PORT environment variable from Render, fallback to 3000
export PORT=${PORT:-3000}

echo "Starting server on port $PORT"

# Start the application
npm start