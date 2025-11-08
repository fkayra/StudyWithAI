#!/usr/bin/env python3
"""
Script to make a user an admin
Usage: python make_admin.py <email>
"""
import sys
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Database setup (same as main.py)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./study_assistant.db")

# check_same_thread is only for SQLite
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# User model (same as main.py)
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    name = Column(String)
    surname = Column(String)
    oauth_provider = Column(String, nullable=True)
    oauth_id = Column(String, nullable=True)
    tier = Column(String, default="free")
    is_admin = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

def make_admin(email: str):
    """Make a user an admin by email"""
    db = SessionLocal()
    try:
        # First, ensure the is_admin column exists
        try:
            # Try to add the column if it doesn't exist
            if DATABASE_URL.startswith("sqlite"):
                try:
                    db.execute(text("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0"))
                    db.commit()
                    print(f"[INFO] Added is_admin column to users table")
                except Exception as e:
                    error_msg = str(e).lower()
                    # Column might already exist, that's fine
                    if "duplicate column" in error_msg or "already exists" in error_msg:
                        db.rollback()
                        print(f"[INFO] is_admin column already exists")
                    else:
                        # Try without text() wrapper for compatibility
                        db.rollback()
                        db.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
                        db.commit()
                        print(f"[INFO] Added is_admin column to users table")
            else:
                # PostgreSQL
                db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin INTEGER DEFAULT 0"))
                db.commit()
                print(f"[INFO] Ensured is_admin column exists")
        except Exception as e:
            error_msg = str(e).lower()
            if "duplicate column" not in error_msg and "already exists" not in error_msg:
                print(f"[WARNING] Could not add is_admin column: {e}")
            db.rollback()
        
        # Find the user
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"❌ Error: User with email '{email}' not found.")
            print("\nAvailable users:")
            users = db.query(User).all()
            if users:
                for u in users:
                    print(f"  - {u.email} (ID: {u.id})")
            else:
                print("  No users found in database.")
            return False
        
        # Make user admin
        user.is_admin = 1
        db.commit()
        
        print(f"✅ Success! User '{email}' is now an admin.")
        print(f"   User ID: {user.id}")
        print(f"   Name: {user.name} {user.surname}")
        print(f"   Tier: {user.tier}")
        print(f"   Admin status: {user.is_admin}")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <email>")
        print("\nExample:")
        print("  python make_admin.py admin@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    make_admin(email)

