# Button Not Working - Troubleshooting Guide

## Quick Fixes

### 1. Make Sure Both Backend and Frontend Are Running

**Terminal 1 - Backend:**
```bash
cd backend
./run.sh   # macOS/Linux
# or
run.bat    # Windows
```

**Terminal 2 - Frontend:**
```bash
cd frontend
./run.sh   # macOS/Linux
# or
run.bat    # Windows
```

### 2. Create an Account First

Most features require you to be logged in:

1. Open http://localhost:3000
2. Click "Sign Up" in the top right
3. Enter email: `test@example.com`
4. Enter password: `testpass123`
5. Click "Sign Up"
6. Now try using the buttons

### 3. Check Browser Console

1. Press `F12` to open Developer Tools
2. Click the "Console" tab
3. Look for error messages (red text)
4. Common errors and fixes:

**"Network Error" or "Failed to fetch"**
- Backend is not running
- Start backend: `cd backend && ./run.sh`

**"401 Unauthorized"**
- You're not logged in
- Go to http://localhost:3000/login

**"CORS error"**
- Backend and frontend URLs don't match
- Check `.env.local` in frontend has `BACKEND_BASE=http://localhost:8000`

### 4. Clear Browser Cache

Sometimes old code gets cached:

1. Press `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
2. Or clear cache manually:
   - Chrome: Settings → Privacy → Clear browsing data
   - Firefox: Settings → Privacy → Clear Data

### 5. Check Environment Variables

**Backend** (`backend/.env`):
```bash
OPENAI_API_KEY=your-openai-api-key-here
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
```

**Frontend** (`frontend/.env.local`):
```bash
BACKEND_BASE=http://localhost:8000
NEXT_PUBLIC_API_BASE=/api
```

## Specific Button Issues

### "Generate Test" Button Not Working

**Symptom:** Clicking the button does nothing

**Fixes:**
1. ✅ Enter a topic in the text area first
2. ✅ Make sure you're logged in (see tier badge in top right)
3. ✅ Check backend is running (`http://localhost:8000/health` should work)
4. ✅ Check browser console for errors

**Testing:**
```bash
# In browser console (F12):
localStorage.getItem('accessToken')
# Should show a token, not null
```

### "Upload Files" Button Not Working

**Symptom:** Redirects to login or nothing happens

**Fixes:**
1. ✅ Log in first
2. ✅ Check backend is running
3. ✅ Verify you haven't exceeded daily quota (2 uploads for free tier)

### Difficulty Level Buttons Not Working

**Symptom:** Clicking difficulty buttons doesn't highlight them

**Fixes:**
1. ✅ Refresh the page
2. ✅ Clear browser cache
3. ✅ Check if JavaScript is enabled in browser

### Navigation Buttons Not Working

**Symptom:** Top navigation links don't work

**Fixes:**
1. ✅ Frontend not running - start with `./run.sh`
2. ✅ Port 3000 blocked - check if something else is using it
3. ✅ Browser extension blocking - try incognito mode

## Testing Button Functionality

### Test 1: Basic Click

1. Open browser console (F12)
2. Type: `console.log('test')`
3. Press Enter
4. If you see "test" printed, JavaScript is working

### Test 2: Check React

1. Right-click on any button
2. Select "Inspect"
3. Look for React DevTools icon in browser toolbar
4. If you see it, React is loaded

### Test 3: Network Requests

1. Open Network tab in DevTools (F12)
2. Click a button
3. Look for new network requests
4. If you see requests, button events are working

## Common Error Messages

### "Please login first to generate tests"
**Fix:** Click the alert OK, then login at `/login`

### "Failed to generate test"
**Causes:**
- Backend not running
- OpenAI API key not set
- Rate limit exceeded
- No internet connection

**Fix:**
```bash
# Check backend .env file:
cat backend/.env

# Should show:
# OPENAI_API_KEY=your-key-here
```

### "Upload quota exceeded"
**Fix:** You've used your daily free uploads. Either:
- Wait until tomorrow
- Upgrade to Premium at `/pricing`

### "Module not found" in console
**Fix:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

## Still Not Working?

### Step-by-Step Debug

1. **Stop everything:**
   ```bash
   # Press Ctrl+C in both terminal windows
   ```

2. **Restart backend:**
   ```bash
   cd backend
   rm -rf __pycache__
   ./run.sh
   # Wait for "Uvicorn running on..."
   ```

3. **Restart frontend (new terminal):**
   ```bash
   cd frontend
   rm -rf .next
   ./run.sh
   # Wait for "Local: http://localhost:3000"
   ```

4. **Test in incognito/private window:**
   - No cache
   - No extensions
   - Fresh start

5. **Create new account:**
   - Sometimes old accounts have issues
   - Use a new email: `test2@example.com`

### Check Versions

```bash
# Python (need 3.9+)
python --version

# Node.js (need 18+)
node --version

# npm (need 9+)
npm --version
```

If versions are too old, update them.

### Port Conflicts

**Backend (port 8000) already in use:**
```bash
# Find what's using it:
lsof -i :8000   # macOS/Linux
netstat -ano | findstr :8000   # Windows

# Kill it or change port:
uvicorn main:app --port 8001
```

**Frontend (port 3000) already in use:**
```bash
# Run on different port:
npm run dev -- -p 3001
```

## Development Mode Issues

### Hot Reload Not Working

Frontend file changes not showing:
```bash
cd frontend
rm -rf .next
npm run dev
```

Backend file changes not showing:
```bash
# Backend auto-reloads with --reload flag
# If not working, restart: Ctrl+C then ./run.sh
```

## Production Issues

If deploying to production and buttons don't work:

1. ✅ Check environment variables are set
2. ✅ Check CORS allows your frontend domain
3. ✅ Check HTTPS is used (not HTTP)
4. ✅ Check API proxy is configured in `next.config.js`

## Getting More Help

If none of this works:

1. **Collect information:**
   - Browser console errors (screenshot)
   - Backend terminal output
   - Frontend terminal output
   - What button you're clicking
   - What happens (nothing, error, redirect, etc.)

2. **Check these files:**
   - `frontend/.env.local` - Should have BACKEND_BASE
   - `backend/.env` - Should have OPENAI_API_KEY
   - Browser DevTools Console (F12) - Any red errors?
   - Browser DevTools Network tab - Any failed requests?

3. **Try the examples:**
   - Login: http://localhost:3000/login
   - Health check: http://localhost:8000/health
   - If health check fails, backend isn't running

## Quick Test Script

Run this to test everything:

```bash
# Test backend
curl http://localhost:8000/health
# Should return: {"status":"healthy","timestamp":"..."}

# Test frontend
curl http://localhost:3000
# Should return HTML

# If both work, the issue is in the browser
```

## Success Checklist

- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000
- [ ] Can access http://localhost:3000
- [ ] Can create an account
- [ ] Can log in
- [ ] Tier badge shows in top right
- [ ] Browser console has no errors
- [ ] Network tab shows requests when clicking buttons

If all checked ✅, buttons should work!
