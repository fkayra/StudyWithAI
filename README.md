# StudyWithAI

An AI-powered study assistant that helps you generate summaries, flashcards, and practice exams from your documents.

## Features

- 📝 **Smart Summaries**: Generate comprehensive study notes from your documents
- 🎴 **Flashcards**: Auto-create flashcards for quick review
- 🎯 **Practice Exams**: AI-generated multiple-choice exams
- 💬 **AI Tutor**: Get explanations and help with questions
- 📊 **Progress Tracking**: Monitor your study history
- 🌐 **Multi-language**: Support for English and Turkish
- 🔐 **User Authentication**: Secure login and registration

## Tech Stack

**Backend:**
- FastAPI (Python web framework)
- SQLite database
- OpenAI API integration
- JWT authentication

**Frontend:**
- Next.js 14 (React framework)
- TypeScript
- Tailwind CSS
- Axios for API calls

## Installation

### Prerequisites

- Python 3.8+
- Node.js 18+
- OpenAI API key

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```env
OPENAI_API_KEY=your_openai_api_key_here
```

5. Start the backend server:

**For local development only:**
```bash
uvicorn main:app --reload --port 8000
```

**For network access (access from other computers):**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- Local: `http://localhost:8000`
- Network: `http://YOUR_IP_ADDRESS:8000` (e.g., `http://192.168.1.100:8000`)

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment variables:
```bash
cp .env.example .env.local
```

Edit `.env.local`:

**For local development:**
```env
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

**For accessing backend from another computer:**
```env
NEXT_PUBLIC_API_BASE=http://192.168.1.100:8000
```
(Replace `192.168.1.100` with your backend server's IP address)

4. Start the frontend:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Network Configuration (Access from Other Computers)

To test the app from another computer on the same network:

### Step 1: Find Your Computer's IP Address

**Windows:**
```bash
ipconfig
```
Look for "IPv4 Address" (e.g., 192.168.1.100)

**Mac/Linux:**
```bash
ifconfig
# or
ip addr show
```
Look for your local IP (e.g., 192.168.1.100)

### Step 2: Configure CORS on Backend

Edit `backend/.env`:
```env
CORS_ORIGINS=http://localhost:3000,http://192.168.1.100:3000,http://192.168.1.101:3000
```
Or for development convenience (allow all origins):
```env
CORS_ORIGINS=*
```

### Step 3: Start Backend with Network Access
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Step 4: Configure Frontend API URL

On the computer running the frontend, edit `frontend/.env.local`:
```env
NEXT_PUBLIC_API_BASE=http://192.168.1.100:8000
```
(Use the IP address from Step 1)

### Step 5: Access the App

You can now access the app from any computer on your network:
- Frontend: `http://192.168.1.100:3000` (or the IP where frontend is running)
- Backend API: `http://192.168.1.100:8000`

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `POST /auth/refresh` - Refresh access token

### File Management
- `POST /upload` - Upload documents (PDF, DOCX, PPTX, TXT)
- `GET /uploads` - List user's uploaded files

### Content Generation
- `POST /summarize-from-files` - Generate summary from documents
- `POST /flashcards-from-files` - Create flashcards
- `POST /exam-from-files` - Generate practice exam
- `POST /ask` - Quick test generator (no file upload required)

### AI Tutor
- `POST /explain` - Get explanation for a question

## Project Structure

```
StudyWithAI/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example        # Environment variables template
│   └── study_assistant.db  # SQLite database (auto-created)
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js pages
│   │   ├── components/     # React components
│   │   └── lib/           # Utilities (API client)
│   ├── package.json
│   └── .env.example       # Frontend environment template
└── README.md
```

## Development

### Backend Development
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Building for Production

**Frontend:**
```bash
cd frontend
npm run build
npm start
```

## Deployment (Production)

### Quick Deploy to Vercel + Railway

**⚡ 5 Dakikalık Hızlı Başlangıç:** [VERCEL_QUICKSTART.md](./VERCEL_QUICKSTART.md)

**📚 Detaylı Rehber:** [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md)

**Kısa Özet:**

1. **Backend'i Deploy Edin** (Railway/Render):
   - Environment variables: `OPENAI_API_KEY`, `JWT_SECRET_KEY`, `CORS_ORIGINS=*`
   - Backend URL'nizi alın (örn: `https://your-app.railway.app`)

2. **Frontend'i Vercel'e Deploy Edin**:
   - Vercel Dashboard → New Project → Import Repository
   - Root Directory: `frontend`
   - Environment Variable: `NEXT_PUBLIC_API_URL=https://your-backend.railway.app`
   - Deploy!

3. **Test Edin**: Vercel URL'nizi açın ve uygulamayı test edin

**Detaylı deployment rehberleri için yukarıdaki dökümanları inceleyin.**

## Troubleshooting

### "Upload failed" or API connection errors

1. **Check if backend is running**: Visit `http://localhost:8000/health`
2. **Verify API URL**: Check `frontend/.env.local` has correct `NEXT_PUBLIC_API_BASE`
3. **Check CORS**: Make sure `backend/.env` includes your frontend URL in `CORS_ORIGINS`
4. **Network access**: If accessing from another computer, use `--host 0.0.0.0` when starting backend

### "OPENAI_API_KEY not found"

Make sure you've created `backend/.env` and added your OpenAI API key.

### CORS Errors

If you see CORS errors in browser console:
1. Check `backend/.env` has `CORS_ORIGINS` configured
2. Restart the backend after changing `.env`
3. For development, you can temporarily use `CORS_ORIGINS=*`

## Environment Variables

### Backend (.env)
```env
OPENAI_API_KEY=required
JWT_SECRET_KEY=optional (auto-generated)
CORS_ORIGINS=optional (defaults to localhost)
STRIPE_SECRET_KEY=optional (for payments)
```

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_BASE=required (API URL)
```

## License

MIT

## Support

For issues and questions, please check the troubleshooting section above or create an issue on GitHub.
