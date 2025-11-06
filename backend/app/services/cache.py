"""
Caching service for summary results
Reduces redundant OpenAI API calls for identical requests
"""
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
import os

# Use existing database connection
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./study_assistant.db")

# Check if we need to handle SQLite connection args
if DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import create_engine
    cache_engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    cache_engine = create_engine(DATABASE_URL)

Base = declarative_base()


class SummaryCache(Base):
    """Cache table for summary results"""
    __tablename__ = "summary_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    request_hash = Column(String, unique=True, index=True)  # SHA256 of request params
    result_json = Column(Text)  # Cached JSON result
    created_at = Column(DateTime, default=datetime.utcnow)
    accessed_at = Column(DateTime, default=datetime.utcnow)  # For LRU cleanup
    access_count = Column(Integer, default=0)  # Hit counter


# Create table if it doesn't exist
Base.metadata.create_all(bind=cache_engine)


def get_cached(request_hash: str, db: Session, ttl_seconds: int = 7 * 24 * 60 * 60) -> Optional[str]:
    """
    Retrieve cached summary result
    Returns None if not found or expired
    """
    try:
        cache_entry = db.query(SummaryCache).filter(
            SummaryCache.request_hash == request_hash
        ).first()
        
        if not cache_entry:
            return None
        
        # Check if expired
        expiry = cache_entry.created_at + timedelta(seconds=ttl_seconds)
        if datetime.utcnow() > expiry:
            # Delete expired entry
            db.delete(cache_entry)
            db.commit()
            return None
        
        # Update access stats
        cache_entry.accessed_at = datetime.utcnow()
        cache_entry.access_count += 1
        db.commit()
        
        return cache_entry.result_json
    
    except Exception as e:
        print(f"Cache retrieval error: {e}")
        return None


def set_cached(request_hash: str, json_text: str, db: Session) -> None:
    """
    Store summary result in cache
    """
    try:
        # Check if entry already exists
        existing = db.query(SummaryCache).filter(
            SummaryCache.request_hash == request_hash
        ).first()
        
        if existing:
            # Update existing
            existing.result_json = json_text
            existing.created_at = datetime.utcnow()
            existing.accessed_at = datetime.utcnow()
            existing.access_count = 0
        else:
            # Create new
            cache_entry = SummaryCache(
                request_hash=request_hash,
                result_json=json_text
            )
            db.add(cache_entry)
        
        db.commit()
    
    except Exception as e:
        print(f"Cache storage error: {e}")
        db.rollback()


def clear_old_cache_entries(db: Session, days: int = 30) -> int:
    """
    Clean up cache entries older than specified days
    Returns number of entries deleted
    """
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = db.query(SummaryCache).filter(
            SummaryCache.accessed_at < cutoff
        ).delete()
        db.commit()
        return deleted
    except Exception as e:
        print(f"Cache cleanup error: {e}")
        db.rollback()
        return 0


def get_cache_stats(db: Session) -> dict:
    """
    Get cache statistics
    """
    try:
        total = db.query(SummaryCache).count()
        total_hits = db.query(SummaryCache).with_entities(
            db.func.sum(SummaryCache.access_count)
        ).scalar() or 0
        
        return {
            "total_entries": total,
            "total_hits": total_hits,
            "avg_hits_per_entry": total_hits / total if total > 0 else 0
        }
    except Exception:
        return {"error": "Failed to get stats"}
