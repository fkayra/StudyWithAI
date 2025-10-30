# AI Study Assistant - Production-Ready Full-Stack Application

A comprehensive AI-powered study assistant that generates grounded exams, flashcards, and summaries from uploaded documents. Built with FastAPI (backend) and Next.js (frontend).

## 🌟 Features

### Core Functionality
- **Document Upload**: Support for PDF, PPTX, DOCX, JPG, PNG files
- **Grounded Content Generation**: All content strictly derived from uploaded documents
- **Smart Exam Generation**: MCQ exams with difficulty levels (İlk-Ortaokul, Lise, Üniversite)
- **Flashcard Creation**: Automatic flashcard generation with evidence citations
- **Summaries**: Structured topic summaries with evidence support
- **AI Tutor**: Explain feature and chat-with-tutor for any question
- **Authentication**: JWT-based auth with email/password
- **Premium Subscriptions**: Stripe integration for paid tiers
- **Quota Management**: Free and premium tier limits

### Security Features
- Server-side API key storage (never exposed to client)
- HTTP-only cookie support for tokens
- Bcrypt password hashing
- CORS protection
- Rate limiting
- JWT with refresh tokens

## 📁 Project Structure

```
/workspace/
├── backend/               # FastAPI backend
│   ├── main.py           # Main application file
│   ├── requirements.txt  # Python dependencies
│   └── .env.example      # Environment variables template
│
├── frontend/             # Next.js frontend
│   ├── src/
│   │   ├── app/          # Next.js 14 app directory
│   │   │   ├── page.tsx           # Home page
│   │   │   ├── login/             # Auth pages
│   │   │   ├── upload/            # File upload
│   │   │   ├── exam/              # Exam interface
│   │   │   ├── flashcards/        # Flashcard viewer
│   │   │   ├── summaries/         # Summary display
│   │   │   ├── account/           # User account
│   │   │   ├── pricing/           # Pricing page
│   │   │   └── legal/             # Legal pages
│   │   ├── components/   # React components
│   │   └── lib/          # Utilities (API client)
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── .env.example
│
└── README.md            # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm/pnpm/yarn

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment**
   
   **Windows:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   
   **macOS/Linux:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your credentials:
   ```
   OPENAI_API_KEY=your-openai-api-key-here
   JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
   STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
   STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
   ```

5. **Run the backend server**
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   
   Backend will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   # or
   pnpm install
   # or
   yarn install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env.local
   ```
   
   Edit `.env.local`:
   ```
   BACKEND_BASE=http://localhost:8000
   NEXT_PUBLIC_API_BASE=/api
   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
   ```

4. **Run the development server**
   ```bash
   npm run dev
   # or
   pnpm dev
   # or
   yarn dev
   ```
   
   Frontend will be available at `http://localhost:3000`

## 🔧 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT tokens
- `POST /auth/refresh` - Refresh access token
- `GET /me` - Get current user info

### File Operations
- `POST /upload` - Upload files (PDF, PPTX, DOCX, JPG, PNG)

### Grounded Generation (from uploaded files)
- `POST /summarize-from-files` - Generate summary from files
- `POST /flashcards-from-files` - Generate flashcards from files
- `POST /exam-from-files` - Generate exam from files

### AI Features
- `POST /ask` - Generate exam from prompt (ungrounded)
- `POST /explain` - Get explanation for a question
- `POST /chat` - Chat with AI tutor

### Billing (Stripe)
- `POST /billing/create-checkout-session` - Create Stripe checkout
- `POST /billing/webhook` - Stripe webhook handler

### Health
- `GET /health` - Health check
- `GET /ping` - Simple ping

## 📊 Database Schema

SQLite database with the following tables:

- **users**: User accounts (id, email, password_hash, tier, created_at)
- **uploads**: File upload records (id, user_id, file_id, filename, mime, size, created_at)
- **usage**: Daily usage tracking (id, user_id, kind, count, date)
- **exams**: Exam history (id, user_id, payload_json, created_at)

## 🎯 Usage Flow

### 1. Upload Documents
1. Navigate to `/upload`
2. Drag and drop or browse files (PDF, PPTX, DOCX, JPG, PNG)
3. Files are uploaded to OpenAI Files API
4. File IDs are stored in session

### 2. Generate Content
**From uploaded files:**
- Click "Summary" to generate structured summaries
- Click "Flashcards" to create study cards
- Click "Exam" to generate MCQ tests

**From prompt:**
- Use home page to enter a topic
- Select difficulty level
- Generate ungrounded exam

### 3. Take Exam
1. Answer all questions (A-D options)
2. Submit exam to see results
3. Click "Explain" for detailed explanations
4. Click "Chat with Tutor" for Q&A

### 4. Manage Account
- View usage quotas in `/account`
- Upgrade to Premium in `/pricing`
- Manage subscription via Stripe portal

## 🔒 Security Best Practices

### Server-Side Only
- OpenAI API key stored in backend `.env`
- Never exposed to client/browser
- All API calls proxied through backend

### Authentication
- JWT tokens with expiration
- Refresh token rotation
- Bcrypt password hashing (salt rounds: auto)

### Rate Limiting
- 30 requests per 5 minutes for AI endpoints
- Per-IP in-memory storage (use Redis in production)

### CORS
- Configured for `localhost:3000` in development
- Restrict to production domain in deployment

## 💰 Quota System

### Free Tier (Daily Limits)
- 2 exam generations
- 5 explanations
- 10 chat messages
- 2 file uploads

### Premium Tier (Daily Limits)
- 100 exam generations
- 500 explanations
- 1000 chat messages
- 100 file uploads

## 🎨 Design System

### Colors
- Background: `#0B1220`
- Text: `#E5E7EB`
- Surface: `#111827` with 85% opacity
- Accent: Gradient from `#6366F1` to `#60A5FA`
- Success: `#22C55E` to `#16A34A`

### Components
- Glass cards with backdrop blur
- Gradient buttons
- Progress bars with animations
- Responsive grid layouts

## 🧪 Testing

### Backend
```bash
# Run with test database
cd backend
pytest tests/
```

### Frontend
```bash
# Run tests
cd frontend
npm test
```

## 📦 Production Deployment

### Backend (Railway/Render/Fly.io)

1. Set environment variables in platform dashboard
2. Deploy from GitHub or CLI
3. Ensure database persistence (SQLite → PostgreSQL recommended)
4. Set up Stripe webhook endpoint

### Frontend (Vercel/Netlify)

1. Connect GitHub repository
2. Set build command: `npm run build`
3. Set output directory: `.next`
4. Configure environment variables
5. Deploy

### Environment Variables (Production)

**Backend:**
- `OPENAI_API_KEY` - Your OpenAI API key
- `JWT_SECRET_KEY` - Strong random string
- `STRIPE_SECRET_KEY` - Live Stripe secret key
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook signing secret

**Frontend:**
- `BACKEND_BASE` - Production backend URL
- `NEXT_PUBLIC_API_BASE` - `/api` (proxied)
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` - Live Stripe publishable key

## 🔍 Troubleshooting

### Backend Issues

**ImportError: No module named 'fastapi'**
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`

**OpenAI API errors**
- Verify `OPENAI_API_KEY` in `.env`
- Check API quota/billing in OpenAI dashboard

**Database locked errors**
- SQLite limitation with concurrent writes
- Use PostgreSQL for production

### Frontend Issues

**Module not found errors**
- Delete `node_modules` and `package-lock.json`
- Run `npm install` again

**API connection refused**
- Ensure backend is running on port 8000
- Check `BACKEND_BASE` in `.env.local`

**CORS errors**
- Verify origin in backend CORS middleware
- Use proxy configuration in `next.config.js`

## 📄 API Response Formats

### Exam Format
```json
{
  "questions": [
    {
      "number": 1,
      "question": "What is...?",
      "options": {
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D"
      }
    }
  ],
  "answer_key": {
    "1": "A",
    "2": "C"
  },
  "grounding": [
    {
      "number": 1,
      "sources": [
        {
          "file_id": "file-123",
          "evidence": "Quote from document..."
        }
      ]
    }
  ]
}
```

### Summary Format
```json
{
  "summary": {
    "title": "Topic Title",
    "sections": [
      {
        "heading": "Section 1",
        "bullets": ["Point 1", "Point 2"]
      }
    ]
  },
  "citations": [
    {
      "file_id": "file-123",
      "evidence": "Supporting quote..."
    }
  ]
}
```

### Flashcard Format
```json
{
  "deck": "Deck Name",
  "cards": [
    {
      "type": "basic",
      "front": "Question or term",
      "back": "Answer or definition",
      "source": {
        "file_id": "file-123",
        "evidence": "Source quote..."
      }
    }
  ]
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/ai-study-assistant/issues)
- Email: support@example.com

## 🙏 Acknowledgments

- OpenAI for GPT-4o-mini API
- FastAPI for the amazing Python framework
- Next.js for the React framework
- Stripe for payment processing
- Tailwind CSS for styling utilities

---

**Built with ❤️ for students everywhere**
