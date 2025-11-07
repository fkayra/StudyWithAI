"""
AI Study Assistant Backend - FastAPI Application
Provides grounded document processing, exam generation, and AI tutoring
"""
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Date, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
import bcrypt
from jose import jwt, JWTError
import os
import re
import requests
from collections import defaultdict
import stripe
import time
from dotenv import load_dotenv
import io
from docx import Document
from pptx import Presentation
from PyPDF2 import PdfReader

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./study_assistant.db")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 43200  # 30 days (30 * 24 * 60)
REFRESH_TOKEN_EXPIRE_DAYS = 90  # 90 days
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Cookie settings - Railway/production detection
# Railway always sets PORT env var, use that as production indicator
IS_PRODUCTION = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RENDER") or os.getenv("PORT"))

# For Railway (production), always use secure cookies with SameSite=none for cross-origin (Vercel + Railway)
# Railway provides HTTPS by default, so secure=True is safe
COOKIE_SECURE = IS_PRODUCTION  # True in production (Railway), False in local dev
COOKIE_SAMESITE = "none" if IS_PRODUCTION else "lax"

print(f"[AUTH CONFIG] IS_PRODUCTION={IS_PRODUCTION}, COOKIE_SECURE={COOKIE_SECURE}, COOKIE_SAMESITE={COOKIE_SAMESITE}")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Rate limiting storage (in-memory, use Redis in production)
rate_limit_store = defaultdict(list)

# File content storage for anonymous users (in-memory)
file_content_store = {}

# ============================================================================
# DATABASE SETUP
# ============================================================================
# check_same_thread is only for SQLite
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    name = Column(String)
    surname = Column(String)
    oauth_provider = Column(String, nullable=True)  # Legacy - not used
    oauth_id = Column(String, nullable=True)  # Legacy - not used
    tier = Column(String, default="free")  # "free" or "premium"
    created_at = Column(DateTime, default=datetime.utcnow)

class Upload(Base):
    __tablename__ = "uploads"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    file_id = Column(String)  # OpenAI file ID (not used anymore)
    filename = Column(String)
    mime = Column(String)
    size = Column(Integer)
    content = Column(String)  # Extracted text content
    created_at = Column(DateTime, default=datetime.utcnow)

class Usage(Base):
    __tablename__ = "usage"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    kind = Column(String)  # "exam", "explain", "chat", "upload"
    count = Column(Integer, default=1)
    date = Column(Date, default=date.today)

class Exam(Base):
    __tablename__ = "exams"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    payload_json = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Folder(Base):
    __tablename__ = "folders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    name = Column(String)
    color = Column(String, nullable=True)  # Hex color for folder (optional)
    icon = Column(String, nullable=True)  # Emoji or icon name (optional)
    created_at = Column(DateTime, default=datetime.utcnow)

class History(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    folder_id = Column(Integer, nullable=True)  # Reference to folders table
    type = Column(String)  # "summary", "flashcards", "truefalse", "exam"
    title = Column(String)
    data_json = Column(String)  # JSON stringified data
    score_json = Column(String, nullable=True)  # JSON stringified score (for truefalse, exam)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ============================================================================
# FASTAPI APP
# ============================================================================
app = FastAPI(title="AI Study Assistant API", version="1.0.0")

# Get CORS origins from environment variable
cors_origins_str = os.getenv("CORS_ORIGINS", "")
if cors_origins_str:
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
else:
    # Default to allow all origins if not specified
    cors_origins = ["*"]

# In production environments, always allow all origins for now
# TODO: Restrict to specific domains in production
if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RENDER") or os.getenv("PORT"):
    cors_origins = ["*"]

# Add CORS middleware with permissive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Add custom CORS headers to all responses as backup
@app.middleware("http")
async def add_cors_headers(request, call_next):
    # Get origin from request
    origin = request.headers.get("origin")
    
    # Handle preflight requests
    if request.method == "OPTIONS":
        response = JSONResponse(content={}, status_code=200)
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin, X-Requested-With"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response
    
    # Let FastAPI handle the request and catch HTTPExceptions properly
    response = await call_next(request)
    
    # Set specific origin instead of wildcard when credentials are used
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin, X-Requested-With"
    response.headers["Access-Control-Expose-Headers"] = "Content-Type, Authorization"
    return response

# ============================================================================
# PYDANTIC MODELS
# ============================================================================
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    surname: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class SummarizeRequest(BaseModel):
    file_ids: Optional[List[str]] = None
    language: Optional[str] = "en"
    outline: Optional[bool] = False
    prompt: Optional[str] = None

class FlashcardsRequest(BaseModel):
    file_ids: Optional[List[str]] = None
    style: Optional[str] = "basic"
    deck_name: Optional[str] = "Study Deck"
    count: Optional[int] = 10
    language: Optional[str] = "en"
    prompt: Optional[str] = None

class TrueFalseRequest(BaseModel):
    file_ids: Optional[List[str]] = None
    count: Optional[int] = 10
    language: Optional[str] = "en"
    prompt: Optional[str] = None

class ExamRequest(BaseModel):
    file_ids: Optional[List[str]] = None
    level: Optional[str] = "high-school"
    count: Optional[int] = 5
    language: Optional[str] = "en"
    prompt: Optional[str] = None

class AskRequest(BaseModel):
    prompt: str
    level: Optional[str] = "high-school"
    count: Optional[int] = 5

class ExplainRequest(BaseModel):
    question: str
    options: Optional[Dict[str, str]] = None
    selected: Optional[str] = None
    correct: Optional[str] = None
    file_ids: Optional[List[str]] = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    file_ids: Optional[List[str]] = None

class CheckoutRequest(BaseModel):
    priceId: str
    successUrl: str
    cancelUrl: str

class FolderCreate(BaseModel):
    name: str
    color: Optional[str] = None
    icon: Optional[str] = None

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None

class FolderResponse(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    icon: Optional[str] = None
    created_at: str
    item_count: int = 0

class HistoryItemCreate(BaseModel):
    type: str  # "summary", "flashcards", "truefalse", "exam"
    title: str
    data: Any  # Will be JSON stringified
    score: Optional[Any] = None  # For truefalse and exam results
    folder_id: Optional[int] = None

class HistoryItemUpdate(BaseModel):
    title: Optional[str] = None
    data: Optional[Any] = None
    score: Optional[Any] = None
    folder_id: Optional[int] = None

class HistoryItemResponse(BaseModel):
    id: int
    type: str
    title: str
    data: Any
    score: Optional[Any] = None
    folder_id: Optional[int] = None
    timestamp: int  # Unix timestamp in milliseconds

# ============================================================================
# DEPENDENCIES
# ============================================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    # Try to get token from cookie first (preferred), then fall back to Authorization header
    token = request.cookies.get("access_token")
    
    # Fallback to Authorization header for backward compatibility
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    
    if not token:
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_id = int(user_id_str)  # Convert string back to int
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

def get_optional_user(request: Request, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> Optional[User]:
    """Get user if authenticated, None otherwise"""
    # Try to get token from cookie first, then fall back to Authorization header
    token = request.cookies.get("access_token")
    
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        
        user_id = int(user_id_str)  # Convert string back to int
        user = db.query(User).filter(User.id == user_id).first()
        return user
    except:
        return None

# ============================================================================
# UTILITIES
# ============================================================================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: int, expires_delta: timedelta) -> str:
    expire = datetime.utcnow() + expires_delta
    payload = {"sub": str(user_id), "exp": expire}  # Convert user_id to string
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def rate_limit(request: Request, limit: int = 30, window: int = 300):
    """Simple in-memory rate limiting: limit requests per window (seconds)"""
    ip = request.client.host
    now = time.time()
    
    # Clean old entries
    rate_limit_store[ip] = [ts for ts in rate_limit_store[ip] if now - ts < window]
    
    if len(rate_limit_store[ip]) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    rate_limit_store[ip].append(now)

def check_quota(db: Session, user: User, kind: str) -> bool:
    """Check if user has quota remaining for the given action"""
    # QUOTAS DISABLED FOR TESTING - Always return True
    return True
    
    # Original quota logic (disabled for testing)
    # if user.tier == "premium":
    #     # Premium users have generous limits
    #     limits = {"exam": 100, "explain": 500, "chat": 1000, "upload": 100}
    # else:
    #     # Free tier limits
    #     limits = {"exam": 2, "explain": 5, "chat": 10, "upload": 2}
    # 
    # today = date.today()
    # usage = db.query(Usage).filter(
    #     Usage.user_id == user.id,
    #     Usage.kind == kind,
    #     Usage.date == today
    # ).first()
    # 
    # current_count = usage.count if usage else 0
    # return current_count < limits.get(kind, 0)

def increment_usage(db: Session, user: User, kind: str):
    """Increment usage counter for the user"""
    today = date.today()
    usage = db.query(Usage).filter(
        Usage.user_id == user.id,
        Usage.kind == kind,
        Usage.date == today
    ).first()
    
    if usage:
        usage.count += 1
    else:
        usage = Usage(user_id=user.id, kind=kind, count=1, date=today)
        db.add(usage)
    
    db.commit()

def get_level_text(level: str) -> str:
    """Map difficulty level to description text"""
    mapping = {
        "elementary-middle": "elementary/middle-school level (core notions, simple language)",
        "high-school": "high-school level (intermediate concepts and applications)",
        "university": "university level (advanced concepts; proofs/applications)"
    }
    return mapping.get(level, "university level (advanced concepts; proofs/applications)")

# ============================================================================
# OPENAI INTEGRATION
# ============================================================================
def extract_text_from_file(file_content: bytes, filename: str, mime: str) -> str:
    """Extract text content from uploaded files"""
    try:
        # PDF
        if mime == "application/pdf" or filename.endswith('.pdf'):
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        
        # DOCX
        elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or filename.endswith('.docx'):
            docx_file = io.BytesIO(file_content)
            doc = Document(docx_file)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        
        # PPTX
        elif mime == "application/vnd.openxmlformats-officedocument.presentationml.presentation" or filename.endswith('.pptx'):
            pptx_file = io.BytesIO(file_content)
            prs = Presentation(pptx_file)
            text = ""
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
            return text.strip()
        
        # Plain text or unknown - try to decode as text
        else:
            try:
                return file_content.decode('utf-8')
            except:
                return file_content.decode('latin-1')
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from {filename}: {str(e)}")

def call_openai_with_context(file_contents: List[str], prompt: str, temperature: float = 0.0) -> str:
    """Call OpenAI API with file contents included in the prompt"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Build messages with system and user roles
    messages = []
    
    if file_contents:
        # Add system message with strict instructions
        messages.append({
            "role": "system",
            "content": "You are a study assistant. You MUST create content based ONLY on the documents provided. Do not use external knowledge. If you generate exam questions, they MUST be about the specific content in the documents, not general topics."
        })
        
        # Add document context
        context = "DOCUMENT CONTENT:\n\n"
        for i, content in enumerate(file_contents, 1):
            context += f"=== Document {i} ===\n{content}\n\n"
        
        context += f"\n{prompt}\n\nREMEMBER: Base your response ONLY on the document content above. Do not use external knowledge."
        
        messages.append({
            "role": "user",
            "content": context
        })
    else:
        messages.append({
            "role": "user",
            "content": prompt
        })
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4000
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"OpenAI API call failed: {response.text}")
    
    return response.json()["choices"][0]["message"]["content"]

def parse_mcq_questions(text: str) -> tuple:
    """Parse MCQ format and return questions, answer key"""
    questions = []
    answer_key = {}
    
    # Split by answer key section
    parts = re.split(r'\n\s*Cevap Anahtarı:\s*\n', text, flags=re.IGNORECASE)
    
    if len(parts) == 2:
        questions_text, answers_text = parts
    else:
        questions_text = text
        answers_text = ""
    
    # Parse questions
    question_pattern = r'(\d+)\.\s+(.*?)(?=\n\d+\.|\nCevap Anahtarı:|$)'
    question_matches = re.findall(question_pattern, questions_text, re.DOTALL)
    
    for number, q_text in question_matches:
        # Parse options
        options_pattern = r'[Aa]\)\s*(.*?)\s*[Bb]\)\s*(.*?)\s*[Cc]\)\s*(.*?)\s*[Dd]\)\s*(.*?)(?:\n|$)'
        options_match = re.search(options_pattern, q_text, re.DOTALL)
        
        if options_match:
            question_text = q_text[:options_match.start()].strip()
            options = {
                "A": options_match.group(1).strip(),
                "B": options_match.group(2).strip(),
                "C": options_match.group(3).strip(),
                "D": options_match.group(4).strip()
            }
            
            questions.append({
                "number": int(number),
                "question": question_text,
                "options": options
            })
    
    # Parse answer key
    if answers_text:
        answer_pattern = r'(\d+)\s*[-–]?\s*([A-Da-d])'
        answer_matches = re.findall(answer_pattern, answers_text)
        
        for num, ans in answer_matches:
            answer_key[num] = ans.upper()
    
    return questions, answer_key

# ============================================================================
# HEALTH ENDPOINTS
# ============================================================================
@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/ping")
async def ping():
    return {"message": "pong"}

@app.options("/{path:path}")
async def options_handler(path: str):
    """Handle OPTIONS requests for CORS preflight"""
    return JSONResponse(content={"status": "ok"})

# ============================================================================
# AUTH ENDPOINTS
# ============================================================================
@app.post("/auth/register")
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if user exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        name=user_data.name,
        surname=user_data.surname,
        tier="free"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"id": user.id, "email": user.email, "name": user.name, "surname": user.surname, "tier": user.tier}

@app.post("/auth/login")
async def login(credentials: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_token(user.id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_token(user.id, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    
    # Set HTTP-only cookies for security
    # Important: path="/" ensures cookie is sent with all requests
    response.set_cookie(
        key="access_token",
        value=access_token,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,  # Only send over HTTPS in production
        samesite=COOKIE_SAMESITE,  # "none" for cross-site (production), "lax" for dev
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert minutes to seconds
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # Convert days to seconds
    )
    
    # Debug log
    print(f"[AUTH] Login successful for user {user.id}, cookies set: secure={COOKIE_SECURE}, samesite={COOKIE_SAMESITE}")
    
    # Also return tokens in response for backward compatibility
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "surname": user.surname,
            "tier": user.tier
        }
    }

@app.post("/auth/refresh")
async def refresh(request: Request, response: Response, refresh_data: dict = None):
    # Try to get refresh token from cookie first, then from request body
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token and refresh_data:
        refresh_token = refresh_data.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        user_id = int(user_id_str)  # Convert string to int
        
        access_token = create_token(user_id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        new_refresh = create_token(user_id, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
        
        # Set new cookies
        response.set_cookie(
            key="access_token",
            value=access_token,
            path="/",
            httponly=True,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        response.set_cookie(
            key="refresh_token",
            value=new_refresh,
            path="/",
            httponly=True,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh,
            "token_type": "bearer"
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@app.post("/auth/logout")
async def logout(response: Response):
    # Clear cookies
    response.delete_cookie(key="access_token", path="/", samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
    response.delete_cookie(key="refresh_token", path="/", samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
    return {"message": "Logged out successfully"}

@app.get("/me")
async def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        # Get today's usage
        today = date.today()
        usage_data = {}
        
        for kind in ["exam", "explain", "chat", "upload"]:
            try:
                usage = db.query(Usage).filter(
                    Usage.user_id == current_user.id,
                    Usage.kind == kind,
                    Usage.date == today
                ).first()
                usage_data[kind] = usage.count if usage else 0
            except Exception as e:
                # If usage table has issues, set to 0 and continue
                usage_data[kind] = 0
        
        return {
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "surname": current_user.surname,
            "tier": current_user.tier,
            "usage": usage_data
        }
    except Exception as e:
        # Log the error and return a 500 with details
        import traceback
        error_details = str(e)
        traceback_str = traceback.format_exc()
        print(f"Error in /me endpoint: {error_details}\n{traceback_str}")
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {error_details}")

# ============================================================================
# FILE UPLOAD ENDPOINT
# ============================================================================
@app.post("/upload")
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    # For demo purposes, allow uploads without authentication but with limits
    if not current_user:
        # Anonymous uploads limited to 1 file
        if len(files) > 1:
            raise HTTPException(status_code=403, detail="Please login to upload multiple files")
    else:
        # Check quota for authenticated users
        if not check_quota(db, current_user, "upload"):
            raise HTTPException(status_code=403, detail="Upload quota exceeded. Please upgrade to Premium.")
    
    results = []
    
    for file in files:
        file_bytes = await file.read()
        
        # Extract text content from file
        try:
            text_content = extract_text_from_file(
                file_bytes, 
                file.filename,
                file.content_type or "application/octet-stream"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to process {file.filename}: {str(e)}")
        
        # Generate a simple file_id for tracking
        import hashlib
        file_id = f"file-{hashlib.md5(file_bytes).hexdigest()[:16]}"
        
        # Save to database if user is authenticated, otherwise use in-memory storage
        if current_user:
            upload = Upload(
                user_id=current_user.id,
                file_id=file_id,
                filename=file.filename,
                mime=file.content_type or "application/octet-stream",
                size=len(file_bytes),
                content=text_content
            )
            db.add(upload)
        else:
            # Store in memory for anonymous users
            file_content_store[file_id] = {
                "filename": file.filename,
                "content": text_content,
                "mime": file.content_type or "application/octet-stream"
            }
        
        results.append({
            "file_id": file_id,
            "filename": file.filename,
            "mime": file.content_type,
            "size": len(file_bytes),
            "content_length": len(text_content)
        })
    
    if current_user:
        db.commit()
        increment_usage(db, current_user, "upload")
    
    return results

# ============================================================================
# GROUNDED ENDPOINTS
# ============================================================================
@app.post("/summarize-from-files")
async def summarize_from_files(
    request: Request,
    req: SummarizeRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Advanced summarization endpoint with:
    - Plan-based limits (free/standard/premium)
    - Map-reduce for large documents
    - SHA256 caching for deduplication
    - Token estimation and adaptive output sizing
    """
    rate_limit(request)
    
    # Import new modular services
    from app.config import PLAN_LIMITS, ALLOWED_EXTS, TOKEN_PER_CHAR
    from app.utils.files import (
        ext_ok, pdf_page_count, approx_tokens_from_text_len,
        sha256_bytes, choose_max_output_tokens, validate_mime_type, basic_antivirus_check
    )
    from app.services.cache import get_cached, set_cached
    from app.services.summary import map_reduce_summary, summarize_no_files
    import json
    import hashlib
    
    # Determine user's plan
    plan = getattr(current_user, "tier", "free") if current_user else "free"
    # Map "premium" to "pro" if needed
    if plan == "premium":
        plan = "pro"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["standard"])
    
    # Require either file_ids or prompt
    if not req.file_ids and not req.prompt:
        raise HTTPException(status_code=400, detail="Please provide either files or a prompt.")
    
    # ========== CASE 1: No files, just prompt ==========
    if not req.file_ids:
        try:
            language = req.language or "en"
            result_json = summarize_no_files(
                topic=req.prompt,
                language=language,
                out_cap=limits.max_output_cap
            )
            
            # Parse and return
            result_json = result_json.strip()
            if result_json.startswith('```'):
                lines = result_json.split('\n')
                if lines[0].strip().startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                result_json = '\n'.join(lines)
            
            try:
                result = json.loads(result_json)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', result_json, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                else:
                    result = {
                        "summary": {
                            "title": "Summary",
                            "sections": [{"heading": "Content", "bullets": [result_json]}]
                        },
                        "citations": []
                    }
            
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")
    
    # ========== CASE 2: Files provided ==========
    
    # Fetch and validate files
    files_data = []  # [(filename, content_bytes, text_content)]
    total_mb = 0.0
    total_pages = 0
    pdf_count = 0
    
    for file_id in req.file_ids:
        # Try database first
        upload = db.query(Upload).filter(Upload.file_id == file_id).first()
        if not upload:
            # Try in-memory storage for anonymous users
            if file_id in file_content_store:
                file_info = file_content_store[file_id]
                filename = file_info["filename"]
                text_content = file_info["content"]
                # Reconstruct bytes for validation (approximate)
                content_bytes = text_content.encode("utf-8", errors="ignore")
            else:
                raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
        else:
            filename = upload.filename
            text_content = upload.content  # Already extracted text
            content_bytes = text_content.encode("utf-8", errors="ignore")
        
        # File type validation
        if not ext_ok(filename, ALLOWED_EXTS):
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {filename}")
        
        # Size tracking
        size_mb = len(content_bytes) / (1024 * 1024)
        total_mb += size_mb
        
        # PDF page count
        if filename.lower().endswith(".pdf"):
            pdf_count += 1
            # For PDF, we'd need original bytes, but we have text already
            # Skip page count validation if we only have text
            # In production, store original bytes too
        
        # Basic security checks
        if not basic_antivirus_check(content_bytes):
            raise HTTPException(status_code=400, detail=f"File failed security check: {filename}")
        
        files_data.append((filename, content_bytes, text_content))
    
    # ========== LIMIT CHECKS ==========
    if len(files_data) > limits.max_files_total:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Your plan allows {limits.max_files_total} files. Upgrade for more."
        )
    
    if pdf_count > limits.max_pdfs:
        raise HTTPException(
            status_code=400,
            detail=f"Too many PDFs. Your plan allows {limits.max_pdfs} PDFs. Upgrade for more."
        )
    
    if total_mb > limits.max_total_mb:
        raise HTTPException(
            status_code=400,
            detail=f"Total file size ({total_mb:.1f} MB) exceeds your plan limit ({limits.max_total_mb} MB)."
        )
    
    # Merge all text content
    merged_text = "\n\n".join([text for _, _, text in files_data if text])
    
    # Token estimation
    estimated_tokens = approx_tokens_from_text_len(len(merged_text), TOKEN_PER_CHAR)
    
    # Hard cap to prevent abuse (5x plan limit)
    HARD_CAP = limits.max_input_tokens * 5
    if estimated_tokens > HARD_CAP:
        raise HTTPException(
            status_code=400,
            detail=f"Content extremely large (~{estimated_tokens} tokens). Maximum is {HARD_CAP} tokens. Please split the upload."
        )
    
    # If content is large (>50% of plan limit), force map-reduce
    force_map_reduce = estimated_tokens > (limits.max_input_tokens // 2)
    
    # Use plan's max output cap directly (always use max for quality)
    # Adaptive sizing was causing too-low limits
    out_cap = limits.max_output_cap
    
    print(f"[SUMMARY CONFIG] Plan: {plan}, max_output_cap: {limits.max_output_cap}, using: {out_cap}")
    
    # ========== CACHE CHECK ==========
    # Create cache key from: plan, language, prompt, file hashes, out_cap, model
    from app.config import OPENAI_MODEL
    cache_key_data = {
        "plan": plan,
        "language": req.language or "en",
        "prompt": (req.prompt or "")[:1000],  # Limit prompt length in cache key
        "out_cap": out_cap,
        "model": OPENAI_MODEL,
        "file_hashes": [sha256_bytes(content) for _, content, _ in files_data]
    }
    cache_key = hashlib.sha256(
        json.dumps(cache_key_data, sort_keys=True).encode()
    ).hexdigest()
    
    # Check cache
    cached_result = get_cached(cache_key, db)
    if cached_result:
        print(f"[CACHE HIT] Returning cached summary for {cache_key[:12]}...")
        return json.loads(cached_result)
    
    # ========== GENERATE SUMMARY ==========
    print(f"[CACHE MISS] Generating new summary (estimated={estimated_tokens} tokens, out_cap={out_cap}, force_map_reduce={force_map_reduce})...")
    
    try:
        from app.utils.json_helpers import parse_json_robust, create_error_response
        from app.utils.quality import enforce_exam_ready, validate_summary_completeness
        from app.services.summary import quality_score
        
        language = req.language or "en"
        additional_instructions = req.prompt or ""
        
        # Use map-reduce pipeline
        result_json = map_reduce_summary(
            full_text=merged_text,
            language=language,
            additional_instructions=additional_instructions,
            out_cap=out_cap,
            force_chunking=force_map_reduce
        )
        
        # Parse JSON with robust error handling
        try:
            result = parse_json_robust(result_json)
            print("[SUMMARY] JSON parsed successfully")
        except ValueError as e:
            print(f"[SUMMARY] All JSON parse attempts failed: {e}")
            result = create_error_response(
                "Failed to parse AI response. This may be due to response format issues.",
                len(result_json)
            )
        
        # Calculate quality score
        score = quality_score(result)
        print(f"[QUALITY GUARDRAIL] Score: {score}/1.0 (threshold: 0.7)")
        
        # Enforce exam-ready quality standards
        result = enforce_exam_ready(result)
        
        # Validate and log warnings
        warnings = validate_summary_completeness(result)
        if warnings:
            print(f"[SUMMARY QUALITY] Warnings: {warnings}")
        
        # Cache the result (only if not error)
        if "error" not in result.get("summary", {}).get("title", "").lower():
            set_cached(cache_key, json.dumps(result), db)
        
        return result
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[SUMMARY ERROR] {error_trace}")
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")

@app.post("/flashcards-from-files")
async def flashcards_from_files(
    request: Request,
    req: FlashcardsRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    rate_limit(request)
    
    # Require either file_ids or prompt
    if not req.file_ids and not req.prompt:
        raise HTTPException(status_code=400, detail="Please provide either files or a prompt.")
    
    # Fetch file contents from database or in-memory storage
    file_contents = []
    if req.file_ids:
        for file_id in req.file_ids:
            # Try database first
            upload = db.query(Upload).filter(Upload.file_id == file_id).first()
            if upload and upload.content:
                file_contents.append(upload.content)
            # Try in-memory storage for anonymous users
            elif file_id in file_content_store:
                file_contents.append(file_content_store[file_id]["content"])
    
    additional_instructions = ""
    if req.prompt:
        additional_instructions = f"\n\nADDITIONAL USER INSTRUCTIONS:\n{req.prompt}\n\nMake sure to follow these instructions while creating flashcards."
    
    language_instruction = ""
    if req.language == "tr":
        language_instruction = "\n\nIMPORTANT: Generate ALL flashcards in TURKISH language."
    elif req.language == "en":
        language_instruction = "\n\nIMPORTANT: Generate ALL flashcards in ENGLISH language."
    
    system_prompt = """You are a study assistant. Create helpful flashcards from the document content or user topics."""
    
    if file_contents:
        user_prompt = f"""Create {req.count} flashcards from the documents. Extract key concepts, questions, or important information.
{language_instruction}
{additional_instructions}

Output as JSON:
{{
  "deck": "{req.deck_name}",
  "cards": [
    {{"type": "{req.style}", "front": "Question or term", "back": "Answer or definition", "source": {{"file_id": "doc", "evidence": "relevant text"}}}}
  ]
}}"""
    else:
        # No files, just prompt
        user_prompt = f"""Create {req.count} flashcards about the topic requested by the user.
{language_instruction}

USER REQUEST:
{req.prompt}

Output as JSON:
{{
  "deck": "{req.deck_name}",
  "cards": [
    {{"type": "{req.style}", "front": "Question or term", "back": "Answer or definition"}}
  ]
}}"""
    
    try:
        response_text = call_openai_with_context(file_contents, f"{system_prompt}\n\n{user_prompt}", temperature=0.0)
        
        import json
        
        # Clean the response to extract JSON
        response_text = response_text.strip()
        
        # Try to find JSON in response
        if response_text.startswith('```'):
            # Remove code blocks
            lines = response_text.split('\n')
            response_text = '\n'.join([l for l in lines if not l.strip().startswith('```')])
        
        try:
            result = json.loads(response_text)
        except:
            # If still fails, try to extract JSON from text
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
            else:
                # Fallback: create cards from the response
                result = {
                    "deck": req.deck_name,
                    "cards": [{"type": req.style, "front": "Content", "back": response_text, "source": {"file_id": "", "evidence": ""}}]
                }
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/truefalse-from-files")
async def truefalse_from_files(
    request: Request,
    req: TrueFalseRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    rate_limit(request)
    
    # Require either file_ids or prompt
    if not req.file_ids and not req.prompt:
        raise HTTPException(status_code=400, detail="Please provide either files or a prompt.")
    
    # Fetch file contents from database or in-memory storage
    file_contents = []
    if req.file_ids:
        for file_id in req.file_ids:
            # Try database first
            upload = db.query(Upload).filter(Upload.file_id == file_id).first()
            if upload and upload.content:
                file_contents.append(upload.content)
            # Try in-memory storage for anonymous users
            elif file_id in file_content_store:
                file_contents.append(file_content_store[file_id]["content"])
    
    additional_instructions = ""
    if req.prompt:
        additional_instructions = f"\n\nADDITIONAL USER INSTRUCTIONS:\n{req.prompt}\n\nMake sure to follow these instructions while creating True/False statements."
    
    language_instruction = ""
    if req.language == "tr":
        language_instruction = "\n\nIMPORTANT: Generate ALL True/False statements in TURKISH language."
    elif req.language == "en":
        language_instruction = "\n\nIMPORTANT: Generate ALL True/False statements in ENGLISH language."
    
    system_prompt = """You are a study assistant. Create True/False statement cards from document content or user topics."""
    
    if file_contents:
        user_prompt = f"""Create {req.count} True/False statement cards from the documents. Each statement should be a factual claim that can be verified as true or false based on the document content.
{language_instruction}
{additional_instructions}

IMPORTANT RULES:
- Each statement should be a clear, factual claim
- Statements should be based ONLY on the document content
- Mix true and false statements (approximately 50/50 or as appropriate)
- For false statements, make them plausible but incorrect based on the content
- Each statement should be standalone and verifiable

Output as JSON:
{{
  "cards": [
    {{"statement": "Statement text here", "answer": true, "explanation": "Brief explanation why this is true/false"}},
    {{"statement": "Another statement", "answer": false, "explanation": "Brief explanation why this is false"}}
  ]
}}

Return ONLY valid JSON, no markdown code blocks, no extra text."""
    else:
        # No files, just prompt
        user_prompt = f"""Create {req.count} True/False statement cards about the topic requested by the user.
{language_instruction}

USER REQUEST:
{req.prompt}

IMPORTANT RULES:
- Each statement should be a clear, factual claim
- Mix true and false statements (approximately 50/50 or as appropriate)
- For false statements, make them plausible but incorrect
- Each statement should be standalone and verifiable

Output as JSON:
{{
  "cards": [
    {{"statement": "Statement text here", "answer": true, "explanation": "Brief explanation why this is true/false"}},
    {{"statement": "Another statement", "answer": false, "explanation": "Brief explanation why this is false"}}
  ]
}}

Return ONLY valid JSON, no markdown code blocks, no extra text."""
    
    try:
        response_text = call_openai_with_context(file_contents, f"{system_prompt}\n\n{user_prompt}", temperature=0.0)
        
        import json
        import re
        
        # Clean the response to extract JSON
        response_text = response_text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            if lines[0].strip().startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            response_text = '\n'.join(lines)
        
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON in the text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                except:
                    # Fallback: create basic structure
                    result = {
                        "cards": [{"statement": "Content", "answer": True, "explanation": response_text}]
                    }
            else:
                # If still fails, wrap in basic structure
                result = {
                    "cards": [{"statement": "Content", "answer": True, "explanation": response_text}]
                }
        
        # Ensure cards have required fields
        if "cards" in result:
            for card in result["cards"]:
                if "answer" not in card:
                    card["answer"] = True
                if "explanation" not in card:
                    card["explanation"] = "No explanation provided"
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/exam-from-files")
async def exam_from_files(
    request: Request,
    req: ExamRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    rate_limit(request)
    
    if current_user and not check_quota(db, current_user, "exam"):
        raise HTTPException(status_code=403, detail="Exam generation quota exceeded")
    
    # Require either file_ids or prompt
    if not req.file_ids and not req.prompt:
        raise HTTPException(status_code=400, detail="Please provide either files or a prompt.")
    
    # Fetch file contents from database or in-memory storage
    file_contents = []
    if req.file_ids:
        for file_id in req.file_ids:
            # Try database first
            upload = db.query(Upload).filter(Upload.file_id == file_id).first()
            if upload and upload.content:
                file_contents.append(upload.content)
            # Try in-memory storage for anonymous users
            elif file_id in file_content_store:
                file_contents.append(file_content_store[file_id]["content"])
    
    level_text = get_level_text(req.level)
    
    additional_instructions = ""
    if req.prompt:
        additional_instructions = f"\n\nADDITIONAL USER INSTRUCTIONS:\n{req.prompt}\n\nMake sure to follow these instructions while creating exam questions."
    
    language_instruction = ""
    if req.language == "tr":
        language_instruction = "\n\nIMPORTANT: Generate ALL exam questions in TURKISH language."
    elif req.language == "en":
        language_instruction = "\n\nIMPORTANT: Generate ALL exam questions in ENGLISH language."
    
    system_prompt = """You are a study assistant. Create exam questions intelligently from documents or user topics."""
    
    if file_contents:
        user_prompt = f"""IMPORTANT: First, analyze the document to determine its type:
{language_instruction}

1. If the document contains EXISTING EXAM QUESTIONS/TESTS:
   - Identify the topics, subjects, and difficulty level
   - Generate {req.count} NEW similar questions on the SAME TOPICS
   - DO NOT ask questions about the exam itself (e.g., "What does question 3 ask?")
   - Instead, create new questions about the same subject matter
   - Example: If the exam has SQL database questions, create NEW SQL questions, not "What table is mentioned in the exam?"

2. If the document contains STUDY MATERIAL (notes, textbooks, lectures):
   - Generate {req.count} questions testing knowledge of the content
   - Ask questions about concepts, definitions, and topics in the material

Difficulty level: {level_text}
{additional_instructions}

Follow this EXACT format:

1. Question text here?
A) Option A
B) Option B
C) Option C
D) Option D

2. Question text here?
A) Option A
B) Option B
C) Option C
D) Option D

Cevap Anahtarı:
1-A, 2-B, ...

Generate questions now based on the document type you identified."""
    else:
        # No files, generate from prompt
        user_prompt = f"""Create {req.count} multiple-choice exam questions on the topic requested by the user.
{language_instruction}

USER REQUEST:
{req.prompt}

Difficulty level: {level_text}

Create educational questions that test understanding of the topic.

Follow this EXACT format:

1. Question text here?
A) Option A
B) Option B
C) Option C
D) Option D

2. Question text here?
A) Option A
B) Option B
C) Option C
D) Option D

Cevap Anahtarı:
1-A, 2-B, ..."""
    
    try:
        response_text = call_openai_with_context(file_contents, f"{system_prompt}\n\n{user_prompt}", temperature=0.0)
        
        # Check for insufficient context
        if "INSUFFICIENT_CONTEXT" in response_text:
            return {"status": "INSUFFICIENT_CONTEXT", "message": response_text}
        
        # Parse questions and answer key
        questions, answer_key = parse_mcq_questions(response_text)
        
        # If no questions were parsed, return error
        if not questions:
            return {
                "status": "ERROR",
                "message": "Could not generate valid questions from the document. Raw response: " + response_text[:500]
            }
        
        result = {
            "questions": questions,
            "answer_key": answer_key,
            "grounding": [{"number": i+1, "sources": [{"file_id": req.file_ids[0] if req.file_ids else "", "evidence": "Based on uploaded documents"}]} for i in range(len(questions))]
        }
        
        if current_user:
            increment_usage(db, current_user, "exam")
            
            # Save exam
            import json
            exam = Exam(user_id=current_user.id, payload_json=json.dumps(result))
            db.add(exam)
            db.commit()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# UNGROUNDED ENDPOINTS
# ============================================================================
@app.post("/ask")
async def ask(
    request: Request,
    req: AskRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    rate_limit(request)
    
    # Try to get user if authenticated, otherwise allow limited access
    current_user = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id_str = payload.get("sub")
            if user_id_str:
                user_id = int(user_id_str)  # Convert string to int
                current_user = db.query(User).filter(User.id == user_id).first()
        except JWTError:
            pass
    
    # Check quota only if user is authenticated
    if current_user and not check_quota(db, current_user, "exam"):
        raise HTTPException(status_code=403, detail="Exam generation quota exceeded. Please upgrade to Premium or try again tomorrow.")
    
    level_text = get_level_text(req.level)
    
    prompt = f"""Create {req.count} multiple-choice questions (A–D) about: {req.prompt}
Difficulty: {level_text}

Follow this EXACT format:

1. Question text here?
A) Option A
B) Option B
C) Option C
D) Option D

2. Question text here?
A) Option A
B) Option B
C) Option C
D) Option D

Cevap Anahtarı:
1-A, 2-B, ..."""
    
    try:
        response_text = call_openai_with_context([], prompt, temperature=0.0)
        
        questions, answer_key = parse_mcq_questions(response_text)
        
        result = {
            "questions": questions,
            "answer_key": answer_key
        }
        
        # Increment usage only if user is authenticated
        if current_user:
            increment_usage(db, current_user, "exam")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/explain")
async def explain(
    request: Request,
    req: ExplainRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    rate_limit(request)
    
    # Try to get user if authenticated
    current_user = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id_str = payload.get("sub")
            if user_id_str:
                user_id = int(user_id_str)  # Convert string to int
                current_user = db.query(User).filter(User.id == user_id).first()
        except JWTError:
            pass
    
    # Check quota only if user is authenticated
    if current_user and not check_quota(db, current_user, "explain"):
        raise HTTPException(status_code=403, detail="Explanation quota exceeded")
    
    # Fetch file contents if file_ids are provided
    file_contents = []
    if req.file_ids:
        for file_id in req.file_ids:
            # Try database first
            upload = db.query(Upload).filter(Upload.file_id == file_id).first()
            if upload and upload.content:
                file_contents.append(upload.content)
            # Try in-memory storage for anonymous users
            elif file_id in file_content_store:
                file_contents.append(file_content_store[file_id]["content"])
    
    prompt = f"""Explain this question concisely:

Question: {req.question}
"""
    
    if req.options:
        for key, val in req.options.items():
            prompt += f"{key}) {val}\n"
    
    if req.selected and req.correct:
        prompt += f"\nSelected: {req.selected}\nCorrect: {req.correct}\n"
    
    if file_contents:
        prompt += """\n\nNOTE: The uploaded document contains reference material. 
If it's an exam/test, use it to understand the topic and context, but explain based on the SUBJECT MATTER, not the document itself.
If it's study material, reference specific information from it.
"""
    
    prompt += "\nProvide a short, targeted explanation in the same language as the question. Justify the correct answer and explain why others are incorrect."
    
    try:
        response_text = call_openai_with_context(file_contents, prompt, temperature=0.2)
        
        # Increment usage only if user is authenticated
        if current_user:
            increment_usage(db, current_user, "explain")
        
        return {"explanation": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(
    request: Request,
    req: ChatRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    rate_limit(request)
    
    # Try to get user if authenticated
    current_user = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id_str = payload.get("sub")
            if user_id_str:
                user_id = int(user_id_str)  # Convert string to int
                current_user = db.query(User).filter(User.id == user_id).first()
        except JWTError:
            pass
    
    # Check quota only if user is authenticated
    if current_user and not check_quota(db, current_user, "chat"):
        raise HTTPException(status_code=403, detail="Chat quota exceeded")
    
    # Fetch file contents if file_ids are provided
    file_contents = []
    if req.file_ids:
        for file_id in req.file_ids:
            # Try database first
            upload = db.query(Upload).filter(Upload.file_id == file_id).first()
            if upload and upload.content:
                file_contents.append(upload.content)
            # Try in-memory storage for anonymous users
            elif file_id in file_content_store:
                file_contents.append(file_content_store[file_id]["content"])
    
    # Build conversation
    conversation = "\n".join([f"{msg.role}: {msg.content}" for msg in req.messages])
    
    try:
        response_text = call_openai_with_context(file_contents, conversation, temperature=0.7)
        
        # Increment usage only if user is authenticated
        if current_user:
            increment_usage(db, current_user, "chat")
        
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# BILLING ENDPOINTS (STRIPE)
# ============================================================================
@app.post("/billing/create-checkout-session")
async def create_checkout_session(
    req: CheckoutRequest,
    current_user: User = Depends(get_current_user)
):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": req.priceId,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=req.successUrl,
            cancel_url=req.cancelUrl,
            client_reference_id=str(current_user.id),
        )
        
        return {"sessionId": session.id, "url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/billing/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe webhook not configured")
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Handle checkout.session.completed
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("client_reference_id")
        
        if user_id:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                user.tier = "premium"
                db.commit()
    
    return {"status": "success"}

# ============================================================================
# HISTORY ENDPOINTS
# ============================================================================
@app.post("/history", response_model=HistoryItemResponse)
async def save_history(
    item: HistoryItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a history item for the authenticated user"""
    import json
    
    # Validate folder_id if provided
    if item.folder_id:
        folder = db.query(Folder).filter(
            Folder.id == item.folder_id,
            Folder.user_id == current_user.id
        ).first()
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
    
    history_entry = History(
        user_id=current_user.id,
        type=item.type,
        title=item.title,
        data_json=json.dumps(item.data),
        score_json=json.dumps(item.score) if item.score else None,
        folder_id=item.folder_id
    )
    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)
    
    return {
        "id": history_entry.id,
        "type": history_entry.type,
        "title": history_entry.title,
        "data": json.loads(history_entry.data_json),
        "score": json.loads(history_entry.score_json) if history_entry.score_json else None,
        "folder_id": history_entry.folder_id,
        "timestamp": int(history_entry.created_at.timestamp() * 1000)
    }

@app.get("/history", response_model=List[HistoryItemResponse])
async def get_history(
    folder_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get history items for the authenticated user, optionally filtered by folder"""
    import json
    
    query = db.query(History).filter(History.user_id == current_user.id)
    
    # Filter by folder if provided
    if folder_id is not None:
        if folder_id == 0:
            # Special case: folder_id=0 means "no folder" (uncategorized)
            query = query.filter(History.folder_id == None)
        else:
            query = query.filter(History.folder_id == folder_id)
    
    history_entries = query.order_by(History.created_at.desc()).all()
    
    return [
        {
            "id": entry.id,
            "type": entry.type,
            "title": entry.title,
            "data": json.loads(entry.data_json),
            "score": json.loads(entry.score_json) if entry.score_json else None,
            "folder_id": entry.folder_id,
            "timestamp": int(entry.created_at.timestamp() * 1000)
        }
        for entry in history_entries
    ]

@app.put("/history/{history_id}", response_model=HistoryItemResponse)
async def update_history_item(
    history_id: int,
    update: HistoryItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a specific history item (e.g., add score after completion or move to folder)"""
    import json
    
    history_entry = db.query(History).filter(
        History.id == history_id,
        History.user_id == current_user.id
    ).first()
    
    if not history_entry:
        raise HTTPException(status_code=404, detail="History item not found")
    
    # Validate folder_id if provided
    if update.folder_id is not None:
        if update.folder_id > 0:  # 0 or None means remove from folder
            folder = db.query(Folder).filter(
                Folder.id == update.folder_id,
                Folder.user_id == current_user.id
            ).first()
            if not folder:
                raise HTTPException(status_code=404, detail="Folder not found")
    
    # Update fields if provided
    if update.title is not None:
        history_entry.title = update.title
    if update.data is not None:
        history_entry.data_json = json.dumps(update.data)
    if update.score is not None:
        history_entry.score_json = json.dumps(update.score)
    if update.folder_id is not None:
        history_entry.folder_id = update.folder_id if update.folder_id > 0 else None
    
    db.commit()
    db.refresh(history_entry)
    
    return {
        "id": history_entry.id,
        "type": history_entry.type,
        "title": history_entry.title,
        "data": json.loads(history_entry.data_json),
        "score": json.loads(history_entry.score_json) if history_entry.score_json else None,
        "folder_id": history_entry.folder_id,
        "timestamp": int(history_entry.created_at.timestamp() * 1000)
    }

@app.delete("/history/{history_id}")
async def delete_history_item(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific history item"""
    history_entry = db.query(History).filter(
        History.id == history_id,
        History.user_id == current_user.id
    ).first()
    
    if not history_entry:
        raise HTTPException(status_code=404, detail="History item not found")
    
    db.delete(history_entry)
    db.commit()
    
    return {"status": "success"}

@app.delete("/history")
async def clear_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear all history for the authenticated user"""
    db.query(History).filter(History.user_id == current_user.id).delete()
    db.commit()
    
    return {"status": "success"}

# ============================================================================
# FOLDER ENDPOINTS
# ============================================================================
@app.post("/folders", response_model=FolderResponse)
async def create_folder(
    folder: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new folder for organizing history items"""
    new_folder = Folder(
        user_id=current_user.id,
        name=folder.name,
        color=folder.color,
        icon=folder.icon
    )
    db.add(new_folder)
    db.commit()
    db.refresh(new_folder)
    
    # Count items in this folder
    item_count = db.query(History).filter(
        History.user_id == current_user.id,
        History.folder_id == new_folder.id
    ).count()
    
    return {
        "id": new_folder.id,
        "name": new_folder.name,
        "color": new_folder.color,
        "icon": new_folder.icon,
        "created_at": new_folder.created_at.isoformat(),
        "item_count": item_count
    }

@app.get("/folders", response_model=List[FolderResponse])
async def get_folders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all folders for the authenticated user"""
    folders = db.query(Folder).filter(
        Folder.user_id == current_user.id
    ).order_by(Folder.created_at.desc()).all()
    
    result = []
    for folder in folders:
        # Count items in this folder
        item_count = db.query(History).filter(
            History.user_id == current_user.id,
            History.folder_id == folder.id
        ).count()
        
        result.append({
            "id": folder.id,
            "name": folder.name,
            "color": folder.color,
            "icon": folder.icon,
            "created_at": folder.created_at.isoformat(),
            "item_count": item_count
        })
    
    return result

@app.put("/folders/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: int,
    update: FolderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a folder"""
    folder = db.query(Folder).filter(
        Folder.id == folder_id,
        Folder.user_id == current_user.id
    ).first()
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Update fields if provided
    if update.name is not None:
        folder.name = update.name
    if update.color is not None:
        folder.color = update.color
    if update.icon is not None:
        folder.icon = update.icon
    
    db.commit()
    db.refresh(folder)
    
    # Count items in this folder
    item_count = db.query(History).filter(
        History.user_id == current_user.id,
        History.folder_id == folder.id
    ).count()
    
    return {
        "id": folder.id,
        "name": folder.name,
        "color": folder.color,
        "icon": folder.icon,
        "created_at": folder.created_at.isoformat(),
        "item_count": item_count
    }

@app.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a folder (history items will become uncategorized)"""
    folder = db.query(Folder).filter(
        Folder.id == folder_id,
        Folder.user_id == current_user.id
    ).first()
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Remove folder_id from all history items in this folder
    db.query(History).filter(
        History.user_id == current_user.id,
        History.folder_id == folder_id
    ).update({"folder_id": None})
    
    db.delete(folder)
    db.commit()
    
    return {"status": "success"}

@app.get("/admin/migrate-database")
@app.post("/admin/migrate-database")
async def migrate_database(db: Session = Depends(get_db)):
    """One-time migration to add name, surname, and folder columns"""
    try:
        # Try to add columns using raw SQL with text()
        if DATABASE_URL.startswith("sqlite"):
            # SQLite
            db.execute(text("ALTER TABLE users ADD COLUMN name TEXT"))
            db.execute(text("ALTER TABLE users ADD COLUMN surname TEXT"))
            db.execute(text("ALTER TABLE history ADD COLUMN folder_id INTEGER"))
            # Create folders table
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS folders (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    name TEXT,
                    color TEXT,
                    icon TEXT,
                    created_at TIMESTAMP
                )
            """))
        else:
            # PostgreSQL
            db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR"))
            db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS surname VARCHAR"))
            db.execute(text("ALTER TABLE history ADD COLUMN IF NOT EXISTS folder_id INTEGER"))
            # Create folders table
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS folders (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    name VARCHAR,
                    color VARCHAR,
                    icon VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
        
        db.commit()
        return {"status": "success", "message": "Database migrated successfully - all columns and tables added"}
    except Exception as e:
        # Columns might already exist or other error
        db.rollback()
        error_msg = str(e)
        
        # Check if columns already exist
        if "already exists" in error_msg.lower() or "duplicate column" in error_msg.lower():
            return {"status": "success", "message": "Columns/tables already exist - no migration needed"}
        
        return {"status": "error", "message": error_msg}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.get("/admin/clear-cache")
@app.delete("/admin/clear-cache")
async def clear_cache(db: Session = Depends(get_db)):
    """Clear all summary cache (admin only - no auth for now)"""
    try:
        from app.services.cache import SummaryCache
        deleted = db.query(SummaryCache).delete()
        db.commit()
        return {"status": "success", "deleted": deleted, "message": "Cache cleared successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
