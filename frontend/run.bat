@echo off

REM AI Study Assistant Frontend - Run Script (Windows)

echo Starting AI Study Assistant Frontend...

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing dependencies...
    npm install
)

REM Check for .env.local file
if not exist ".env.local" (
    echo .env.local file not found. Creating from template...
    copy .env.example .env.local
    echo Please edit .env.local with your configuration.
)

REM Run the application
echo Starting development server on http://localhost:3000...
npm run dev
