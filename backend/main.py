"""
AI Study Assistant Backend - FastAPI Application
Provides grounded document processing, exam generation, and AI tutoring
"""
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Date
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
DATABASE_URL = "sqlite:///./study_assistant.db"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Rate limiting storage (in-memory, use Redis in production)
rate_limit_store = defaultdict(list)

# File content storage for anonymous users (in-memory)
file_content_store = {}

# ============================================================================
# DATABASE SETUP
# ============================================================================
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
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

Base.metadata.create_all(bind=engine)

# ============================================================================
# FASTAPI APP
# ============================================================================
app = FastAPI(title="AI Study Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# PYDANTIC MODELS
# ============================================================================
class UserRegister(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class SummarizeRequest(BaseModel):
    file_ids: List[str]
    language: Optional[str] = "en"
    outline: Optional[bool] = False

class FlashcardsRequest(BaseModel):
    file_ids: List[str]
    style: Optional[str] = "basic"
    deck_name: Optional[str] = "Study Deck"
    count: Optional[int] = 10

class ExamRequest(BaseModel):
    file_ids: List[str]
    level: Optional[str] = "lise"
    count: Optional[int] = 5

class AskRequest(BaseModel):
    prompt: str
    level: Optional[str] = "lise"
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

# ============================================================================
# DEPENDENCIES
# ============================================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split(" ")[1]
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

def get_optional_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> Optional[User]:
    """Get user if authenticated, None otherwise"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    try:
        token = authorization.split(" ")[1]
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
        "ilkokul-ortaokul": "elementary/middle-school level (core notions, simple language)",
        "lise": "high-school level (intermediate concepts and applications)",
        "universite": "university level (advanced concepts; proofs/applications)"
    }
    return mapping.get(level, "high-school level (intermediate concepts and applications)")

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
        tier="free"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"id": user.id, "email": user.email, "tier": user.tier}

@app.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_token(user.id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_token(user.id, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        user_id = int(user_id_str)  # Convert string to int
        
        access_token = create_token(user_id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        new_refresh = create_token(user_id, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh,
            "token_type": "bearer"
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@app.get("/me")
async def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Get today's usage
    today = date.today()
    usage_data = {}
    
    for kind in ["exam", "explain", "chat", "upload"]:
        usage = db.query(Usage).filter(
            Usage.user_id == current_user.id,
            Usage.kind == kind,
            Usage.date == today
        ).first()
        usage_data[kind] = usage.count if usage else 0
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "tier": current_user.tier,
        "usage": usage_data
    }

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
    rate_limit(request)
    
    # Fetch file contents from database or in-memory storage
    file_contents = []
    for file_id in req.file_ids:
        # Try database first
        upload = db.query(Upload).filter(Upload.file_id == file_id).first()
        if upload and upload.content:
            file_contents.append(upload.content)
        # Try in-memory storage for anonymous users
        elif file_id in file_content_store:
            file_contents.append(file_content_store[file_id]["content"])
    
    if not file_contents:
        raise HTTPException(status_code=400, detail="No file content found. Please upload files first.")
    
    system_prompt = """You are a study assistant. Analyze the documents provided and create a helpful summary."""
    
    user_prompt = f"""Create a structured summary from the documents. Even if the content is brief, extract key points and organize them.

IMPORTANT: Return ONLY valid JSON, no markdown code blocks, no extra text.

Output format:
{{
  "summary": {{
    "title": "Document Summary",
    "sections": [
      {{"heading": "Main Points", "bullets": ["point 1", "point 2"]}}
    ]
  }},
  "citations": [
    {{"file_id": "doc", "evidence": "key information from the document"}}
  ]
}}

Return pure JSON only, no ```json``` markers."""
    
    try:
        response_text = call_openai_with_context(file_contents, f"{system_prompt}\n\n{user_prompt}", temperature=0.0)
        
        # Clean the response to extract JSON
        import json
        import re
        
        # Remove markdown code blocks if present
        response_text = response_text.strip()
        if response_text.startswith('```'):
            # Remove code block markers
            lines = response_text.split('\n')
            # Remove first line if it's ```json or ```
            if lines[0].strip().startswith('```'):
                lines = lines[1:]
            # Remove last line if it's ```
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
                    # If still fails, wrap in basic structure
                    result = {
                        "summary": {
                            "title": "Summary",
                            "sections": [{"heading": "Content", "bullets": [response_text]}]
                        },
                        "citations": []
                    }
            else:
                # If not JSON, wrap in a basic structure
                result = {
                    "summary": {
                        "title": "Summary",
                        "sections": [{"heading": "Content", "bullets": [response_text]}]
                    },
                    "citations": []
                }
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/flashcards-from-files")
async def flashcards_from_files(
    request: Request,
    req: FlashcardsRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    rate_limit(request)
    
    # Fetch file contents from database or in-memory storage
    file_contents = []
    for file_id in req.file_ids:
        # Try database first
        upload = db.query(Upload).filter(Upload.file_id == file_id).first()
        if upload and upload.content:
            file_contents.append(upload.content)
        # Try in-memory storage for anonymous users
        elif file_id in file_content_store:
            file_contents.append(file_content_store[file_id]["content"])
    
    if not file_contents:
        raise HTTPException(status_code=400, detail="No file content found. Please upload files first.")
    
    system_prompt = """You are a study assistant. Create helpful flashcards from the document content."""
    
    user_prompt = f"""Create {req.count} flashcards from the documents. Extract key concepts, questions, or important information.

Output as JSON:
{{
  "deck": "{req.deck_name}",
  "cards": [
    {{"type": "{req.style}", "front": "Question or term", "back": "Answer or definition", "source": {{"file_id": "doc", "evidence": "relevant text"}}}}
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
    
    # Fetch file contents from database or in-memory storage
    file_contents = []
    for file_id in req.file_ids:
        # Try database first
        upload = db.query(Upload).filter(Upload.file_id == file_id).first()
        if upload and upload.content:
            file_contents.append(upload.content)
        # Try in-memory storage for anonymous users
        elif file_id in file_content_store:
            file_contents.append(file_content_store[file_id]["content"])
    
    if not file_contents:
        raise HTTPException(status_code=400, detail="No file content found. Please upload files first.")
    
    level_text = get_level_text(req.level)
    
    system_prompt = """You are a study assistant. Analyze the uploaded document and create exam questions intelligently."""
    
    user_prompt = f"""IMPORTANT: First, analyze the document to determine its type:

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
