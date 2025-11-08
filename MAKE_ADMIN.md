# How to Make Your First Admin User

Since there's no admin user yet, you need to create one manually. Here are several methods:

## Method 1: Using the Python Script (Recommended - Easiest)

1. **Make sure you have a user account first:**
   - Register a user account through the web interface (or use an existing account)

2. **Run the make_admin script:**
   ```bash
   cd backend
   python make_admin.py your-email@example.com
   ```

   Example:
   ```bash
   python make_admin.py admin@studywithai.com
   ```

3. **That's it!** The script will:
   - Add the `is_admin` column if it doesn't exist
   - Find the user by email
   - Set them as an admin
   - Display confirmation

## Method 2: Using SQLite Database Directly

If you're using SQLite (default):

1. **Open the database:**
   ```bash
   sqlite3 study_assistant.db
   ```

2. **First, add the is_admin column (if it doesn't exist):**
   ```sql
   ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0;
   ```

3. **Make a user an admin:**
   ```sql
   UPDATE users SET is_admin = 1 WHERE email = 'your-email@example.com';
   ```

4. **Verify:**
   ```sql
   SELECT id, email, name, is_admin FROM users;
   ```

5. **Exit:**
   ```sql
   .quit
   ```

## Method 3: Using PostgreSQL Database

If you're using PostgreSQL:

1. **Connect to your database:**
   ```bash
   psql $DATABASE_URL
   ```
   Or:
   ```bash
   psql -h localhost -U your_user -d your_database
   ```

2. **Add the is_admin column (if it doesn't exist):**
   ```sql
   ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin INTEGER DEFAULT 0;
   ```

3. **Make a user an admin:**
   ```sql
   UPDATE users SET is_admin = 1 WHERE email = 'your-email@example.com';
   ```

4. **Verify:**
   ```sql
   SELECT id, email, name, is_admin FROM users;
   ```

5. **Exit:**
   ```sql
   \q
   ```

## Method 4: Using Python Interactive Shell

1. **Open Python in the backend directory:**
   ```bash
   cd backend
   python
   ```

2. **Run these commands:**
   ```python
   import os
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker
   from dotenv import load_dotenv
   
   load_dotenv()
   DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./study_assistant.db")
   engine = create_engine(DATABASE_URL)
   SessionLocal = sessionmaker(bind=engine)
   
   from main import User
   
   db = SessionLocal()
   user = db.query(User).filter(User.email == 'your-email@example.com').first()
   if user:
       user.is_admin = 1
       db.commit()
       print(f"User {user.email} is now an admin!")
   else:
       print("User not found!")
   db.close()
   ```

## Method 5: Using the Migration Endpoint + Database Update

1. **First, run the migration endpoint to add the is_admin column:**
   ```bash
   curl -X POST http://localhost:8000/admin/migrate-database
   ```
   Or visit: `http://localhost:8000/admin/migrate-database` in your browser

2. **Then use Method 2 or 3 above to update the user**

## Verification

After making a user an admin:

1. **Log out and log back in** (if you're already logged in)
2. **Check the navigation bar** - you should see an "🔧 Admin" link
3. **Visit `/admin`** - you should see the admin panel
4. **Check the `/me` endpoint:**
   ```bash
   curl http://localhost:8000/me
   ```
   Should show `"is_admin": true` in the response

## Troubleshooting

### "User not found"
- Make sure the user exists in the database
- Check the email spelling (case-sensitive)
- List all users first to see available emails

### "Column already exists" error
- This is fine! The column already exists, you can proceed with the UPDATE statement

### "Permission denied" error
- Make sure you have write permissions to the database file
- Check database connection settings

### Admin panel still not visible
- Clear your browser cookies and log in again
- Make sure the `is_admin` field is set to `1` (not `0` or `NULL`)
- Check browser console for errors

## Quick Start (Recommended)

1. Register a user account at `/register`
2. Run: `cd backend && python make_admin.py your-email@example.com`
3. Log out and log back in
4. You should see the Admin link in the navigation!

