#!/bin/bash

# AI Study Assistant Backend - Run Script

echo "🚀 Starting AI Study Assistant Backend..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your actual credentials before continuing."
    exit 1
fi

# Run the application
echo "Starting server on http://localhost:8000..."
uvicorn main:app --reload --port 8000
