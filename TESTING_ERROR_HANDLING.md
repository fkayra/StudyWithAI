# Testing Error Handling - Step by Step Guide

## Quick Test Instructions

### Step 1: Start Backend Server

Open a terminal and run:

```bash
cd /Users/nuricanozcan/Desktop/studywithai/StudyWithAI-1/backend
python -m venv venv  # Only if you haven't created venv before
source venv/bin/activate  # On Mac/Linux
# OR: venv\Scripts\activate  # On Windows

pip install -r requirements.txt  # Only if not installed already

# Start the server
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Step 2: Start Frontend Server

Open a **NEW terminal** (keep backend running) and run:

```bash
cd /Users/nuricanozcan/Desktop/studywithai/StudyWithAI-1/frontend
npm install  # Only if not installed already

npm run dev
```

You should see:
```
- ready started server on 0.0.0.0:3000
- Local:        http://localhost:3000
```

### Step 3: Test Login Error Handling

1. **Open your browser** and go to: `http://localhost:3000/login`

2. **Try to login with wrong credentials:**
   - Email: `wrong@example.com`
   - Password: `wrongpassword123`
   - Click "Login"

3. **Expected Result:**
   - ✅ You should see a **red error box** above the form
   - ✅ Error message: "Invalid email or password"
   - ✅ Page should **NOT refresh**
   - ✅ Form should stay on the page
   - ✅ You can try again without losing your input

### Step 4: Test Registration Error Handling

1. Go to: `http://localhost:3000/register`

2. **Try to register with existing email:**
   - Email: `test@example.com` (or any email that already exists)
   - Password: `password123`
   - Confirm Password: `password123`
   - Click "Sign Up"

3. **Expected Result:**
   - ✅ You should see a **red error box** with the error message
   - ✅ Error message: "Email already registered" (or similar)
   - ✅ Page should **NOT refresh**
   - ✅ Form should stay on the page

### Step 5: Test Network Error (Optional)

To test network error handling:

1. **Stop the backend server** (press Ctrl+C in backend terminal)
2. Try to login with any credentials
3. **Expected Result:**
   - ✅ Error message: "Network error. Please check your connection."
   - ✅ Page should **NOT refresh**

## Visual Checklist

When testing, verify these things:

- [ ] ❌ Wrong credentials → ✅ Red error box appears
- [ ] ❌ Wrong credentials → ✅ Page does NOT refresh
- [ ] ❌ Wrong credentials → ✅ Error message is clear and readable
- [ ] ❌ Wrong credentials → ✅ Form stays on page (can try again)
- [ ] ❌ Backend offline → ✅ Network error message appears

## Quick Commands Reference

**Backend (Terminal 1):**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Frontend (Terminal 2):**
```bash
cd frontend
npm run dev
```

**Browser:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Backend Health: http://localhost:8000/health

## Troubleshooting

### Backend won't start?
- Check if port 8000 is already in use
- Make sure you're in the `backend` directory
- Check if virtual environment is activated

### Frontend won't start?
- Check if port 3000 is already in use
- Make sure you're in the `frontend` directory
- Run `npm install` if dependencies are missing

### No error showing?
- Check browser console (F12) for JavaScript errors
- Check backend terminal for errors
- Make sure backend is running on port 8000



