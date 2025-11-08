# Admin Panel Documentation

## Overview

The admin panel allows administrators to manage users, subscriptions, and view system statistics.

## Features

### 1. User Management
- View all users with their details (email, name, tier, admin status)
- Edit user information (name, surname, tier, admin status)
- Delete users (with cascade deletion of related data)
- View user statistics (usage, history count, uploads count)

### 2. Statistics Dashboard
- Total users count
- Premium users count
- Total history items
- Recent registrations (last 7 days)
- Today's usage statistics

### 3. System Management
- Clear cache
- View quality statistics
- View low-quality patterns

## How to Make a User an Admin

### Option 1: Using the Admin Panel (if you already have an admin)
1. Log in as an existing admin
2. Go to the Admin Panel
3. Find the user you want to make an admin
4. Click "Edit"
5. Check the "Admin" checkbox
6. Click "Save"

### Option 2: Using Database Directly (for first admin)
If you don't have an admin yet, you need to set one directly in the database:

#### SQLite:
```sql
UPDATE users SET is_admin = 1 WHERE email = 'your-admin-email@example.com';
```

#### PostgreSQL:
```sql
UPDATE users SET is_admin = 1 WHERE email = 'your-admin-email@example.com';
```

### Option 3: Using Python Script
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./study_assistant.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Make user admin
user = db.query(User).filter(User.email == 'your-admin-email@example.com').first()
if user:
    user.is_admin = 1
    db.commit()
    print(f"User {user.email} is now an admin")
else:
    print("User not found")
```

## Database Migration

The `is_admin` field is automatically added to the users table when you run the migration endpoint:

```
GET/POST /admin/migrate-database
```

This endpoint:
- Adds the `is_admin` column to the users table (if it doesn't exist)
- Sets default value to 0 (false) for existing users
- Creates any other missing tables/columns

## Admin API Endpoints

All admin endpoints require authentication and admin privileges:

### Users
- `GET /admin/users` - List all users
- `GET /admin/users/{user_id}` - Get user details
- `PUT /admin/users/{user_id}` - Update user
- `DELETE /admin/users/{user_id}` - Delete user

### Statistics
- `GET /admin/stats` - Get admin statistics
- `GET /admin/quality-stats` - Get quality statistics
- `GET /admin/low-quality-patterns` - Get low-quality patterns

### System
- `DELETE /admin/clear-cache` - Clear summary cache

## Security

- Admin endpoints are protected by the `get_admin_user` dependency
- Only users with `is_admin = 1` can access admin endpoints
- Admins cannot remove their own admin status
- Admins cannot delete their own account
- All admin actions are logged (via FastAPI logging)

## Frontend

The admin panel is accessible at `/admin` and is only visible to users with `is_admin = true`.

The admin link appears in the navigation bar for admin users.

## Usage

1. **View Users**: The admin panel displays all users in a table format
2. **Edit User**: Click "Edit" on any user to modify their information
3. **Change Subscription Tier**: Update the tier field (free, standard, premium, pro)
4. **Make Admin**: Check the "Admin" checkbox to grant admin privileges
5. **Delete User**: Click "Delete" to remove a user (cascade deletes related data)
6. **View Statistics**: Statistics are displayed at the top of the admin panel
7. **Clear Cache**: Use the "Clear Cache" button to clear the summary cache

## Notes

- The `is_admin` field is stored as an integer (0 or 1) for SQLite compatibility
- Admin status is checked on every admin endpoint request
- Users without admin status will receive a 403 Forbidden error
- The admin panel automatically redirects non-admin users to the dashboard

