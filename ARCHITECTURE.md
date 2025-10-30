# System Architecture

## Overview

The AI Study Assistant is a full-stack application following a modern client-server architecture with clear separation of concerns.

```
┌─────────────────────────────────────────────────────────────┐
│                         CLIENT                              │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Next.js 14 (React + TypeScript + Tailwind)          │ │
│  │  - Server-side rendering                              │ │
│  │  - API route proxying                                 │ │
│  │  - Client-side state management                       │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ HTTP/REST
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      API GATEWAY                            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Next.js API Routes (Proxy)                          │ │
│  │  - Request forwarding                                 │ │
│  │  - CORS handling                                      │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND SERVER                          │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  FastAPI (Python)                                     │ │
│  │  ┌─────────────────────────────────────────────────┐ │ │
│  │  │  Auth Layer (JWT)                               │ │ │
│  │  ├─────────────────────────────────────────────────┤ │ │
│  │  │  Rate Limiting                                  │ │ │
│  │  ├─────────────────────────────────────────────────┤ │ │
│  │  │  Quota Management                               │ │ │
│  │  ├─────────────────────────────────────────────────┤ │ │
│  │  │  Business Logic                                 │ │ │
│  │  │  - File processing                              │ │ │
│  │  │  - Content generation                           │ │ │
│  │  │  - Grounding validation                         │ │ │
│  │  └─────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         │              │                │
         │              │                │
         ▼              ▼                ▼
┌──────────────┐  ┌──────────┐  ┌────────────────┐
│  Database    │  │  OpenAI  │  │    Stripe      │
│  (SQLite/    │  │   API    │  │  Payment API   │
│  PostgreSQL) │  │          │  │                │
└──────────────┘  └──────────┘  └────────────────┘
```

## Component Breakdown

### Frontend (Next.js)

**Technology Stack:**
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Axios (HTTP client)
- Stripe.js (payment UI)

**Key Components:**

1. **Pages** (`src/app/`)
   - Home: Main entry point with prompt input
   - Upload: File upload interface
   - Exam: Interactive exam taking
   - Flashcards: Card flip interface
   - Summaries: Structured content display
   - Account: User profile and usage
   - Pricing: Subscription plans
   - Auth: Login/Register

2. **Components** (`src/components/`)
   - Navigation: Top navigation bar
   - AuthProvider: Context for auth state
   
3. **Libraries** (`src/lib/`)
   - API Client: Axios instance with interceptors

**Data Flow:**
```
User Action → React Component → API Client → 
  → Next.js API Route (proxy) → Backend → 
    → Response → State Update → UI Render
```

### Backend (FastAPI)

**Technology Stack:**
- FastAPI (web framework)
- SQLAlchemy (ORM)
- Bcrypt (password hashing)
- PyJWT (JWT tokens)
- Stripe (billing)
- Requests (OpenAI API client)

**Architecture Layers:**

1. **Presentation Layer** (Endpoints)
   - REST API endpoints
   - Request/response validation (Pydantic)
   - Error handling

2. **Security Layer**
   - JWT authentication
   - Password hashing
   - CORS middleware
   - Rate limiting

3. **Business Logic Layer**
   - File upload to OpenAI
   - Content generation
   - Grounding validation
   - Quota enforcement

4. **Data Access Layer**
   - SQLAlchemy models
   - Database operations
   - Usage tracking

**Request Processing Flow:**
```
HTTP Request → CORS Check → Auth Middleware → 
  → Rate Limit → Quota Check → Business Logic → 
    → Database/API Calls → Response
```

### Database Schema

**Users Table**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    tier VARCHAR DEFAULT 'free',
    created_at DATETIME DEFAULT NOW()
);
```

**Uploads Table**
```sql
CREATE TABLE uploads (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    file_id VARCHAR NOT NULL,
    filename VARCHAR NOT NULL,
    mime VARCHAR NOT NULL,
    size INTEGER NOT NULL,
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Usage Table**
```sql
CREATE TABLE usage (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    kind VARCHAR NOT NULL,
    count INTEGER DEFAULT 1,
    date DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Exams Table**
```sql
CREATE TABLE exams (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### External Services

#### OpenAI API Integration

**Files API** (`https://api.openai.com/v1/files`)
- Purpose: Upload documents for processing
- Supported formats: PDF, DOCX, PPTX, JPG, PNG
- Flow:
  1. User uploads file to backend
  2. Backend uploads to OpenAI Files API
  3. Receives `file_id`
  4. Stores `file_id` in database

**Chat Completions API** (`https://api.openai.com/v1/chat/completions`)
- Purpose: Content generation
- Model: `gpt-4o-mini`
- Usage:
  - Summaries (temp=0.0)
  - Flashcards (temp=0.0)
  - Exams (temp=0.0)
  - Explanations (temp=0.2)
  - Chat (temp=0.7)

**Grounding Strategy:**
```python
# Reference file IDs in prompt
prompt = f"""
Context: Files {file_ids}
Only use content from these files.

{user_instruction}
"""
```

#### Stripe Integration

**Checkout Flow:**
```
User clicks "Upgrade" → Backend creates Checkout Session →
  → Redirect to Stripe → Payment → Webhook →
    → Backend updates user.tier → Success redirect
```

**Webhook Events:**
- `checkout.session.completed`: Upgrade user to premium
- Signature verification for security

## Security Architecture

### Authentication Flow

```
1. User Registration:
   Email/Password → Hash password (bcrypt) → Store in DB

2. User Login:
   Email/Password → Verify hash → Generate JWT tokens →
     → Access token (60 min) + Refresh token (30 days)

3. Authenticated Request:
   Request + Bearer token → Verify JWT → Extract user_id →
     → Load user → Process request

4. Token Refresh:
   Refresh token → Verify → Generate new tokens → Return
```

### Authorization

**Quota System:**
```python
def check_quota(user, action):
    limits = LIMITS[user.tier][action]
    usage = get_today_usage(user, action)
    return usage < limits
```

**Rate Limiting:**
```python
# In-memory store (use Redis in production)
rate_limits = defaultdict(list)

def rate_limit(ip, limit=30, window=300):
    timestamps = rate_limits[ip]
    recent = [t for t in timestamps if now - t < window]
    if len(recent) >= limit:
        raise RateLimitError
    recent.append(now)
    rate_limits[ip] = recent
```

## Data Flow Examples

### 1. Upload & Generate Exam Flow

```
┌──────┐    1. Upload Files    ┌─────────┐
│ User │ ───────────────────> │ Backend │
└──────┘                       └─────────┘
                                    │
                                    │ 2. Upload to OpenAI
                                    ▼
                              ┌──────────┐
                              │  OpenAI  │
                              │  Files   │
                              └──────────┘
                                    │
                                    │ 3. Return file_ids
                                    ▼
                              ┌─────────┐
                              │ Backend │
                              └─────────┘
                                    │
                                    │ 4. Store in DB
                                    ▼
                              ┌──────────┐
                              │    DB    │
                              └──────────┘
                                    │
                                    │ 5. Return to user
                                    ▼
┌──────┐    6. Request Exam    ┌─────────┐
│ User │ ───────────────────> │ Backend │
└──────┘                       └─────────┘
                                    │
                                    │ 7. Call with file_ids
                                    ▼
                              ┌──────────┐
                              │  OpenAI  │
                              │   API    │
                              └──────────┘
                                    │
                                    │ 8. Generated exam
                                    ▼
                              ┌─────────┐
                              │ Backend │
                              └─────────┘
                                    │
                                    │ 9. Parse & validate
                                    │ 10. Return JSON
                                    ▼
                              ┌──────┐
                              │ User │
                              └──────┘
```

### 2. Authentication Flow

```
┌──────┐    1. Login (email/pwd)  ┌─────────┐
│ User │ ──────────────────────> │ Backend │
└──────┘                          └─────────┘
                                       │
                                       │ 2. Query user
                                       ▼
                                  ┌──────┐
                                  │  DB  │
                                  └──────┘
                                       │
                                       │ 3. User record
                                       ▼
                                  ┌─────────┐
                                  │ Backend │
                                  └─────────┘
                                       │
                                       │ 4. Verify password (bcrypt)
                                       │ 5. Generate JWT tokens
                                       ▼
┌──────┐    6. Access + Refresh    ┌─────────┐
│ User │ <──────────────────────── │ Backend │
└──────┘                            └─────────┘
    │
    │ 7. Store in localStorage
    ▼
┌──────────────┐
│ localStorage │
└──────────────┘
```

## Performance Considerations

### Caching Strategy

1. **Client-Side**
   - Session storage for uploaded file IDs
   - Auth tokens in localStorage
   - React component state

2. **Server-Side** (Future)
   - Redis for rate limit counters
   - Cache OpenAI responses (with caution)
   - Database query results

### Optimization Points

1. **Database**
   - Index on `user_id`, `email`, `date`
   - Connection pooling
   - Query optimization

2. **API Calls**
   - Batch file uploads
   - Streaming responses
   - Timeout handling

3. **Frontend**
   - Code splitting
   - Image optimization
   - Lazy loading

## Scalability

### Horizontal Scaling

```
┌────────┐
│  LB    │  Load Balancer
└────────┘
    │
    ├──────────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ API-1  │ │ API-2  │ │ API-3  │ │ API-N  │
└────────┘ └────────┘ └────────┘ └────────┘
    │          │          │          │
    └──────────┴──────────┴──────────┘
                   │
                   ▼
              ┌────────┐
              │  DB    │  Shared Database
              └────────┘
                   │
                   ▼
              ┌────────┐
              │ Redis  │  Shared Cache
              └────────┘
```

### Bottlenecks & Solutions

1. **OpenAI API Rate Limits**
   - Solution: Queue system, retry logic

2. **Database Locks (SQLite)**
   - Solution: Migrate to PostgreSQL

3. **In-Memory Rate Limiting**
   - Solution: Redis with TTL

4. **File Upload Size**
   - Solution: Chunked uploads, CDN

## Monitoring & Observability

### Key Metrics

1. **API Metrics**
   - Request rate
   - Response time
   - Error rate
   - Status code distribution

2. **Business Metrics**
   - Daily active users
   - Exams generated
   - Files uploaded
   - Conversion rate (free → premium)

3. **System Metrics**
   - CPU/Memory usage
   - Database connections
   - OpenAI API costs
   - Error logs

### Logging Strategy

```python
# Structured logging
logger.info("exam_generated", extra={
    "user_id": user.id,
    "file_count": len(file_ids),
    "question_count": len(questions),
    "duration_ms": elapsed
})
```

## Future Enhancements

1. **Real-time Features**
   - WebSocket for live chat
   - Progress indicators

2. **Advanced AI**
   - Multi-modal content (images + text)
   - Adaptive difficulty
   - Spaced repetition

3. **Collaboration**
   - Shared study sets
   - Group exams
   - Leaderboards

4. **Analytics**
   - Performance tracking
   - Learning curves
   - Weak topic identification

5. **Infrastructure**
   - Microservices architecture
   - Event-driven design
   - Message queue (RabbitMQ/SQS)
