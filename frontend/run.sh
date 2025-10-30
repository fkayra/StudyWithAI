#!/bin/bash

# AI Study Assistant Frontend - Run Script

echo "🚀 Starting AI Study Assistant Frontend..."

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Check for .env.local file
if [ ! -f ".env.local" ]; then
    echo "⚠️  .env.local file not found. Creating from template..."
    cp .env.example .env.local
    echo "⚠️  Please edit .env.local with your configuration."
fi

# Run the application
echo "Starting development server on http://localhost:3000..."
npm run dev
