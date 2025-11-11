"""
Centralized token usage tracking service
Solves session scope issues by creating fresh session when needed
"""
from typing import Optional
from datetime import datetime
import os


def log_token_usage(
    user_id: Optional[int],
    endpoint: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    estimated_cost: float
):
    """
    Log token usage to database with proper session management
    Creates fresh session to avoid scope issues
    """
    try:
        # Import here to avoid circular dependencies
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./study_assistant.db")
        
        # Create engine with minimal settings
        if DATABASE_URL.startswith("sqlite"):
            engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        else:
            engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            print(f"[TOKEN TRACKER] Recording: user_id={user_id}, endpoint={endpoint}, total={total_tokens}")
            
            sql = text("""
                INSERT INTO token_usage (user_id, endpoint, model, input_tokens, output_tokens, total_tokens, estimated_cost, created_at)
                VALUES (:user_id, :endpoint, :model, :input_tokens, :output_tokens, :total_tokens, :estimated_cost, :created_at)
            """)
            
            db.execute(sql, {
                "user_id": user_id,
                "endpoint": endpoint,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "estimated_cost": estimated_cost,
                "created_at": datetime.utcnow()
            })
            db.commit()
            print(f"[TOKEN TRACKER] ✅ Successfully recorded {total_tokens} tokens for user {user_id}, cost: ${estimated_cost:.4f}")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"[TOKEN TRACKER ERROR] ❌ Failed to record token usage: {e}")
        import traceback
        traceback.print_exc()
