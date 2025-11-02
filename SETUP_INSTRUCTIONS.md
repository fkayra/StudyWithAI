# 🚀 Setup Instructions for Testing from Another Computer

## ❗ Important: Update Your Code First

If you're getting `name 'call_openai_responses' is not defined` error, your backend code is outdated.

### Step 1: Update Your Code

On your local computer where you're running the backend:

```bash
# Navigate to your project directory
cd /path/to/StudyWithAI

# Pull latest changes
git pull origin cursor/handle-api-internal-server-error-876c

# Or if you're on a different branch:
git fetch origin
git checkout cursor/handle-api-internal-server-error-876c
git pull
```

### Step 2: Restart Backend

After pulling the latest code, restart your backend:

```bash
# Stop the current backend (Ctrl+C)

# Navigate to backend directory
cd backend

# Restart with network access
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 🌐 Network Configuration (For Testing from Another Computer)

### 1. Find Your Backend Computer's IP Address

**On Windows:**
```cmd
ipconfig
```
Look for "IPv4 Address" (example: 192.168.1.100)

**On Mac/Linux:**
```bash
ifconfig
# or
ip addr show
```

### 2. Configure Backend

Create/edit `backend/.env`:
```env
OPENAI_API_KEY=your_actual_openai_key_here
CORS_ORIGINS=*
```

**Important:** The `*` allows all origins (good for development/testing)

### 3. Start Backend with Network Access

```bash
cd backend

# Activate virtual environment if you have one
# source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate     # Windows

# Start backend with --host 0.0.0.0 (THIS IS CRUCIAL!)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 4. Test Backend is Accessible

From the same computer, visit: `http://localhost:8000/health`

From another computer on the same network: `http://192.168.1.100:8000/health`
(Replace 192.168.1.100 with your actual IP)

If you see JSON response, backend is working!

### 5. Configure Frontend

On the computer where you'll run the frontend:

Create/edit `frontend/.env.local`:
```env
NEXT_PUBLIC_API_BASE=http://192.168.1.100:8000
```
(Replace 192.168.1.100 with your backend computer's IP)

### 6. Start Frontend

```bash
cd frontend
npm install  # Only needed first time
npm run dev
```

### 7. Access from Any Computer

Now you can access the app from any computer on the same network:
- `http://192.168.1.100:3000` (replace with frontend computer's IP)
- Or `http://localhost:3000` if accessing from the same computer

## 🔍 Troubleshooting

### Error: "call_openai_responses is not defined"
**Solution:** Your backend code is outdated. Do `git pull` and restart backend.

### Error: "Upload failed" or "Cannot connect to backend"
**Solutions:**
1. Make sure backend is running: Check `http://YOUR_IP:8000/health`
2. Make sure you started backend with `--host 0.0.0.0`
3. Check firewall isn't blocking port 8000
4. Verify `NEXT_PUBLIC_API_BASE` in `frontend/.env.local` has correct IP
5. Make sure `CORS_ORIGINS=*` in `backend/.env`

### Error: "OPENAI_API_KEY not found"
**Solution:** Create `backend/.env` and add your OpenAI API key

### Backend shows but frontend doesn't connect
**Solution:** 
1. Check `frontend/.env.local` has correct backend IP
2. Restart frontend after changing `.env.local`
3. Clear browser cache or try incognito mode

### Can't access from another computer
**Solutions:**
1. Backend MUST be started with `--host 0.0.0.0` (not just `--host localhost`)
2. Check your computer's firewall settings
3. Make sure both computers are on the same network
4. Try pinging the backend computer: `ping 192.168.1.100`

## 📝 Quick Reference

### Backend Start Command
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Environment
```env
# frontend/.env.local
NEXT_PUBLIC_API_BASE=http://YOUR_BACKEND_IP:8000
```

### Backend Environment
```env
# backend/.env
OPENAI_API_KEY=sk-...your-key...
CORS_ORIGINS=*
```

## ✅ Verification Checklist

Before testing from another computer:

- [ ] Git pulled latest changes
- [ ] Backend `.env` has OpenAI API key
- [ ] Backend `.env` has `CORS_ORIGINS=*`
- [ ] Backend started with `--host 0.0.0.0`
- [ ] Backend health endpoint works: `http://YOUR_IP:8000/health`
- [ ] Frontend `.env.local` has correct backend IP
- [ ] Frontend restarted after changing `.env.local`
- [ ] Both computers on same WiFi/network

## 🎯 Example Setup

**Scenario:** Testing from laptop while backend runs on desktop

**Desktop (Backend) IP:** 192.168.1.100  
**Laptop (Frontend) IP:** 192.168.1.101

**On Desktop:**
```bash
# backend/.env
OPENAI_API_KEY=sk-proj-abc123...
CORS_ORIGINS=*

# Start backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**On Laptop:**
```bash
# frontend/.env.local
NEXT_PUBLIC_API_BASE=http://192.168.1.100:8000

# Start frontend
cd frontend
npm run dev
```

**Access:** Open browser on laptop: `http://localhost:3000`

**Bonus:** Other people on same network can also access: `http://192.168.1.101:3000`
