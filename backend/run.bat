@echo off

REM AI Study Assistant Backend - Run Script (Windows)

echo Starting AI Study Assistant Backend...

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check for .env file
if not exist ".env" (
    echo .env file not found. Creating from template...
    copy .env.example .env
    echo Please edit .env with your actual credentials before continuing.
    pause
    exit /b 1
)

REM Run the application
echo Starting server on http://localhost:8000...
uvicorn main:app --reload --port 8000
