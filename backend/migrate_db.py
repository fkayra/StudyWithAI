"""
Database migration script to add name and surname columns to users table
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "study_assistant.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at {DB_PATH}")
        print("Database will be created automatically when the backend starts.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add name column if it doesn't exist
        if 'name' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN name TEXT")
            print("✓ Added 'name' column to users table")
        else:
            print("✓ 'name' column already exists")
        
        # Add surname column if it doesn't exist
        if 'surname' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN surname TEXT")
            print("✓ Added 'surname' column to users table")
        else:
            print("✓ 'surname' column already exists")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
