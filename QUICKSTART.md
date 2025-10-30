# Quick Start Guide

Get the AI Study Assistant running in 5 minutes!

## Prerequisites

- Python 3.9+ installed
- Node.js 18+ installed
- OpenAI API key (provided in requirements)

## Step 1: Backend Setup (2 minutes)

### Option A: Automatic (Recommended)

**macOS/Linux:**
```bash
cd backend
chmod +x run.sh
./run.sh
```

**Windows:**
```cmd
cd backend
run.bat
```

### Option B: Manual

```bash
cd backend
python -m venv .venv

# Activate virtual environment
# Windows: .\.venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt

# Copy and edit .env file
cp .env.example .env
# Edit .env with your OpenAI API key

uvicorn main:app --reload --port 8000
```

The backend will start at `http://localhost:8000`

## Step 2: Frontend Setup (2 minutes)

Open a NEW terminal window:

### Option A: Automatic (Recommended)

**macOS/Linux:**
```bash
cd frontend
chmod +x run.sh
./run.sh
```

**Windows:**
```cmd
cd frontend
run.bat
```

### Option B: Manual

```bash
cd frontend
npm install

# Copy and edit .env.local file
cp .env.example .env.local

npm run dev
```

The frontend will start at `http://localhost:3000`

## Step 3: Start Using (1 minute)

1. Open browser to `http://localhost:3000`
2. Click "Sign Up" and create an account
3. Login with your credentials
4. Try one of these workflows:

### Workflow A: Upload Documents
1. Click "Upload Files"
2. Drag and drop a PDF/DOCX/PPTX file
3. Click "Summary" or "Flashcards" or "Exam"

### Workflow B: Generate from Prompt
1. On home page, enter a topic (e.g., "Photosynthesis")
2. Select difficulty level
3. Click "Generate Test"
4. Take the exam and see results

## Common Issues

### Backend won't start
- Make sure Python 3.9+ is installed: `python --version`
- Activate virtual environment first
- Check that port 8000 is not in use

### Frontend won't start
- Make sure Node.js 18+ is installed: `node --version`
- Delete `node_modules` and run `npm install` again
- Check that port 3000 is not in use

### Can't connect to backend
- Ensure backend is running on port 8000
- Check `.env.local` has `BACKEND_BASE=http://localhost:8000`

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Configure Stripe for premium features
- Deploy to production (see README.md)

## Support

Need help? Check the [README.md](README.md) troubleshooting section.
