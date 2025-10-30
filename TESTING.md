# Testing Guide

## Overview

This guide covers testing strategies and procedures for the AI Study Assistant.

## Backend Testing

### Manual Testing

#### 1. Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy", "timestamp": "..."}

curl http://localhost:8000/ping
# Expected: {"message": "pong"}
```

#### 2. User Registration
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
# Expected: {"id": 1, "email": "test@example.com", "tier": "free"}
```

#### 3. User Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
# Expected: {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}
```

#### 4. Get Current User
```bash
# Save token from login
TOKEN="your_access_token_here"

curl http://localhost:8000/me \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"id": 1, "email": "test@example.com", "tier": "free", "usage": {...}}
```

#### 5. File Upload
```bash
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@test.pdf"
# Expected: [{"file_id": "file-...", "filename": "test.pdf", ...}]
```

#### 6. Generate Exam (Ungrounded)
```bash
curl -X POST http://localhost:8000/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "photosynthesis",
    "level": "lise",
    "count": 3
  }'
# Expected: {"questions": [...], "answer_key": {...}}
```

#### 7. Explain Question
```bash
curl -X POST http://localhost:8000/explain \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is photosynthesis?",
    "options": {
      "A": "Process of making food",
      "B": "Process of breathing",
      "C": "Process of reproduction",
      "D": "Process of digestion"
    },
    "selected": "B",
    "correct": "A"
  }'
# Expected: {"explanation": "..."}
```

### Automated Testing with Pytest

**Install pytest:**
```bash
pip install pytest pytest-asyncio httpx
```

**Create `tests/test_api.py`:**
```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_register():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "testpass123"
        })
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_login():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register
        await client.post("/auth/register", json={
            "email": "test2@example.com",
            "password": "testpass123"
        })
        
        # Login
        response = await client.post("/auth/login", json={
            "email": "test2@example.com",
            "password": "testpass123"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_protected_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Try without token
        response = await client.get("/me")
        assert response.status_code == 401
        
        # Register and login
        await client.post("/auth/register", json={
            "email": "test3@example.com",
            "password": "testpass123"
        })
        login_response = await client.post("/auth/login", json={
            "email": "test3@example.com",
            "password": "testpass123"
        })
        token = login_response.json()["access_token"]
        
        # Try with token
        response = await client.get("/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        assert response.json()["email"] == "test3@example.com"
```

**Run tests:**
```bash
cd backend
pytest tests/
```

## Frontend Testing

### Manual Testing Checklist

#### Authentication Flow
- [ ] Navigate to `/register`
- [ ] Enter email and password
- [ ] Submit form
- [ ] Verify redirect to home page
- [ ] Verify navigation shows user tier
- [ ] Logout
- [ ] Navigate to `/login`
- [ ] Enter credentials
- [ ] Verify successful login

#### Upload Flow
- [ ] Navigate to `/upload`
- [ ] Drag and drop a PDF file
- [ ] Verify file appears in list
- [ ] Upload additional files
- [ ] Click "Summary" button
- [ ] Verify redirect to `/summaries`
- [ ] Verify summary is displayed

#### Exam Flow
- [ ] Navigate to home page
- [ ] Enter topic: "photosynthesis"
- [ ] Select difficulty: "Lise"
- [ ] Click "Generate Test"
- [ ] Verify 5 questions displayed
- [ ] Select answers for all questions
- [ ] Click "Submit Exam"
- [ ] Verify score displayed
- [ ] Click "Explain" on a question
- [ ] Verify explanation appears
- [ ] Click "Chat with Tutor"
- [ ] Enter message and send
- [ ] Verify response appears

#### Flashcards Flow
- [ ] Upload documents
- [ ] Click "Flashcards"
- [ ] Verify flashcard displayed
- [ ] Click card to flip
- [ ] Click "Next" button
- [ ] Verify next card shown
- [ ] Click "Export Deck"
- [ ] Verify JSON file downloaded

#### Account Flow
- [ ] Navigate to `/account`
- [ ] Verify email and tier displayed
- [ ] Verify usage bars shown
- [ ] (For free users) Click "View Pricing"
- [ ] Verify redirect to pricing page

#### Pricing Flow
- [ ] Navigate to `/pricing`
- [ ] Verify Free and Premium plans shown
- [ ] Click "Upgrade to Premium" (if free user)
- [ ] Verify Stripe checkout opens
- [ ] Cancel checkout
- [ ] Verify return to pricing page

### Browser Testing

Test on multiple browsers:
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

Test on multiple screen sizes:
- Mobile (375px)
- Tablet (768px)
- Desktop (1920px)

### Accessibility Testing

- [ ] Keyboard navigation works
- [ ] All interactive elements have focus states
- [ ] Color contrast meets WCAG AA standards
- [ ] Screen reader compatible
- [ ] No accessibility errors in Lighthouse

## Integration Testing

### End-to-End Flow Test

**Test Case: Complete User Journey**

1. **Setup**
   - Start backend server
   - Start frontend server
   - Clear browser storage

2. **Registration**
   - Navigate to `/register`
   - Enter: `e2e@example.com` / `testpass123`
   - Submit
   - Verify: Redirected to home, logged in

3. **Upload File**
   - Navigate to `/upload`
   - Upload: `test-document.pdf`
   - Verify: File ID received and stored

4. **Generate Summary**
   - Click "Summary"
   - Wait for generation
   - Verify: Summary with sections displayed
   - Verify: Citations present

5. **Generate Flashcards**
   - Go back to `/upload`
   - Click "Flashcards"
   - Wait for generation
   - Verify: Flashcards displayed
   - Click to flip
   - Navigate through cards
   - Export deck
   - Verify: JSON file contains cards

6. **Generate Exam**
   - Go back to `/upload`
   - Click "Exam"
   - Wait for generation
   - Verify: Questions displayed
   - Answer all questions
   - Submit exam
   - Verify: Score calculated correctly

7. **Use AI Features**
   - Click "Explain" on question
   - Verify: Explanation appears
   - Click "Chat with Tutor"
   - Send message: "Can you explain this more?"
   - Verify: Response received

8. **Check Quotas**
   - Navigate to `/account`
   - Verify: Usage incremented
   - Verify: Free tier limits shown

9. **Cleanup**
   - Logout
   - Clear test data

### Load Testing

**Simple load test with Apache Bench:**
```bash
# Test health endpoint
ab -n 1000 -c 10 http://localhost:8000/health

# Test with authentication (save token to file first)
ab -n 100 -c 5 -H "Authorization: Bearer $TOKEN" http://localhost:8000/me
```

**With Locust:**

**Create `locustfile.py`:**
```python
from locust import HttpUser, task, between

class StudyAssistantUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login
        response = self.client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def view_account(self):
        self.client.get("/me", headers=self.headers)
    
    @task(1)
    def generate_exam(self):
        self.client.post("/ask", headers=self.headers, json={
            "prompt": "test topic",
            "level": "lise",
            "count": 5
        })
```

**Run:**
```bash
pip install locust
locust -f locustfile.py --host http://localhost:8000
# Open browser to http://localhost:8089
```

## Security Testing

### 1. SQL Injection
Try malicious inputs in forms:
- Email: `test@example.com'; DROP TABLE users; --`
- Expected: Input sanitized, no effect

### 2. JWT Token Validation
```bash
# Try expired token
curl -H "Authorization: Bearer expired_token" http://localhost:8000/me
# Expected: 401 Unauthorized

# Try malformed token
curl -H "Authorization: Bearer invalid" http://localhost:8000/me
# Expected: 401 Unauthorized

# Try no token
curl http://localhost:8000/me
# Expected: 401 Unauthorized
```

### 3. Rate Limiting
```bash
# Rapid requests
for i in {1..35}; do curl http://localhost:8000/ask; done
# Expected: 429 Too Many Requests after 30 requests
```

### 4. CORS
```bash
# Request from unauthorized origin
curl -H "Origin: https://evil.com" http://localhost:8000/health
# Expected: CORS error or no CORS headers
```

## Performance Testing

### Response Time Benchmarks

| Endpoint | Target | Notes |
|----------|--------|-------|
| `/health` | < 10ms | No DB calls |
| `/auth/login` | < 100ms | DB + hashing |
| `/upload` | < 5s | OpenAI API call |
| `/ask` | < 10s | OpenAI generation |
| `/explain` | < 5s | OpenAI generation |

### Database Query Optimization

**Slow query log:**
```python
import time

@app.middleware("http")
async def log_slow_queries(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    if duration > 1.0:  # Log queries > 1 second
        logger.warning(f"Slow request: {request.url} took {duration:.2f}s")
    
    return response
```

## Troubleshooting Tests

### Test Failures

**"Connection refused"**
- Ensure backend/frontend is running
- Check port numbers

**"Invalid token"**
- Token may have expired
- Re-login and get fresh token

**"Rate limit exceeded"**
- Wait 5 minutes
- Or restart backend to clear in-memory store

**"OpenAI API error"**
- Check API key in `.env`
- Verify API quota not exceeded

### CI/CD Integration

**GitHub Actions example:**
```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt
      - run: cd backend && pytest tests/
  
  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
        with:
          node-version: '18'
      - run: cd frontend && npm install
      - run: cd frontend && npm test
```

## Test Data

### Sample Documents

Create test files for upload testing:
- `test.pdf`: Simple PDF with text
- `test.docx`: Word document
- `test.pptx`: PowerPoint presentation
- `test.jpg`: Image file

### Sample Prompts

For exam generation testing:
- "Photosynthesis in plants"
- "World War II history"
- "Quadratic equations"
- "Chemical bonding"
- "Shakespeare's Hamlet"

## Coverage Goals

- Backend: > 80% code coverage
- Frontend: > 70% code coverage
- Critical paths: 100% coverage (auth, billing, file upload)
