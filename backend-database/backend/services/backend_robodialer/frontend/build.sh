#!/bin/bash
# Render.com build script for Next.js application

echo "Starting build process..."

# Install dependencies
npm install

# Build the application
npm run build

echo "Build completed successfully!"

# Verify build output
if [ -d ".next" ]; then
    echo "✅ Build output exists"
else
    echo "❌ Build failed - no .next directory found"
    exit 1
fi

echo "Ready for deployment!"