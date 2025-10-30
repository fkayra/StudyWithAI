# Getting Started - AI Study Assistant

Welcome! This guide will get your AI Study Assistant up and running in less than 10 minutes.

## 📋 Prerequisites Check

Before starting, verify you have:

- [ ] **Python 3.9+** installed
  ```bash
  python --version
  # Should show: Python 3.9.x or higher
  ```

- [ ] **Node.js 18+** installed
  ```bash
  node --version
  # Should show: v18.x.x or higher
  ```

- [ ] **npm** installed (comes with Node.js)
  ```bash
  npm --version
  # Should show: 9.x.x or higher
  ```

- [ ] **OpenAI API Key** (provided in requirements)

## 🚀 Quick Start

### Step 1: Backend Setup (3 minutes)

1. **Open Terminal 1** and navigate to backend:
   ```bash
   cd backend
   ```

2. **Run the startup script:**
   
   **macOS/Linux:**
   ```bash
   chmod +x run.sh
   ./run.sh
   ```
   
   **Windows:**
   ```cmd
   run.bat
   ```

3. **On first run**, the script will:
   - Create a virtual environment
   - Install all dependencies
   - Create `.env` from template
   - Prompt you to add your API key

4. **Edit `.env` file:**
   - Open `backend/.env` in a text editor
   - Replace the OpenAI API key if needed
   - Save the file

5. **Run the script again:**
   ```bash
   ./run.sh    # macOS/Linux
   run.bat     # Windows
   ```

6. **Verify backend is running:**
   - You should see: "Uvicorn running on http://127.0.0.1:8000"
   - Open browser to: http://localhost:8000/health
   - Should show: `{"status": "healthy", "timestamp": "..."}`

✅ **Backend is ready!**

### Step 2: Frontend Setup (3 minutes)

1. **Open Terminal 2** (keep backend running) and navigate to frontend:
   ```bash
   cd frontend
   ```

2. **Run the startup script:**
   
   **macOS/Linux:**
   ```bash
   chmod +x run.sh
   ./run.sh
   ```
   
   **Windows:**
   ```cmd
   run.bat
   ```

3. **Wait for installation** (first run only):
   - Dependencies will be installed automatically
   - This may take 1-2 minutes

4. **Verify frontend is running:**
   - You should see: "Local: http://localhost:3000"
   - Browser should automatically open
   - If not, manually open: http://localhost:3000

✅ **Frontend is ready!**

## 🎯 Test the Application (3 minutes)

### Test 1: Create an Account

1. **Navigate to**: http://localhost:3000
2. **Click**: "Sign Up" in the top right
3. **Enter**:
   - Email: `test@example.com`
   - Password: `testpass123`
   - Confirm Password: `testpass123`
4. **Click**: "Sign Up"
5. **Verify**: You're redirected to the home page
6. **Check**: Top right shows "Free" tier badge

✅ **Account creation works!**

### Test 2: Generate an Exam

1. **On the home page**:
   - Topic field: Enter `"Photosynthesis"`
   - Difficulty: Select `"Lise"` (High School)
2. **Click**: "Generate Test"
3. **Wait**: 5-10 seconds for generation
4. **Verify**: 5 questions are displayed
5. **Answer**: Select A/B/C/D for each question
6. **Click**: "Submit Exam"
7. **Verify**: Score is calculated and displayed

✅ **Exam generation works!**

### Test 3: Try Upload (Optional)

1. **Click**: "Upload" in the navigation
2. **Create a test file**: Save a simple text as `test.txt` (or use any PDF)
3. **Drag and drop**: File into the upload area
4. **Wait**: A few seconds
5. **Verify**: File appears in the uploaded files list

✅ **Upload works!**

### Test 4: Try Explain Feature

1. **Go back to your exam**
2. **Click**: "Explain" under any question
3. **Verify**: Explanation appears below the question

✅ **Explain feature works!**

### Test 5: Check Account

1. **Click**: Your tier badge in top right
2. **Verify**: You see:
   - Your email
   - Tier: "Free"
   - Usage bars showing your activity

✅ **Account page works!**

## 🎉 Success!

Your AI Study Assistant is now fully operational!

## 📚 What's Next?

### Learn More
- Read [README.md](README.md) for full documentation
- Check [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system
- Review [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment

### Customize
1. **Change Branding**: Edit colors in `frontend/tailwind.config.js`
2. **Adjust Quotas**: Modify limits in `backend/main.py`
3. **Add Features**: Extend existing code

### Deploy to Production
1. Follow [DEPLOYMENT.md](DEPLOYMENT.md)
2. Set up PostgreSQL database
3. Configure Stripe for payments
4. Deploy to Railway/Vercel

## 🆘 Troubleshooting

### Backend Issues

**"ModuleNotFoundError: No module named 'fastapi'"**
- Solution: Activate virtual environment first
  ```bash
  # macOS/Linux
  source .venv/bin/activate
  
  # Windows
  .\.venv\Scripts\activate
  ```

**"Port 8000 is already in use"**
- Solution: Kill the process or change port
  ```bash
  # Find process
  lsof -i :8000  # macOS/Linux
  
  # Change port in run script or:
  uvicorn main:app --port 8001
  ```

**"OpenAI API error"**
- Solution: Check your API key in `.env`
- Verify it starts with `sk-proj-`
- Check OpenAI dashboard for quota

### Frontend Issues

**"Module not found"**
- Solution: Delete and reinstall
  ```bash
  rm -rf node_modules package-lock.json
  npm install
  ```

**"Port 3000 is already in use"**
- Solution: Kill process or use different port
  ```bash
  npm run dev -- -p 3001
  ```

**"Cannot connect to backend"**
- Solution: 
  - Ensure backend is running on port 8000
  - Check `.env.local` has `BACKEND_BASE=http://localhost:8000`

### Both Not Working?

1. **Restart everything**:
   - Stop both terminals (Ctrl+C)
   - Close terminals
   - Open fresh terminals
   - Start backend first, then frontend

2. **Check prerequisites**:
   ```bash
   python --version   # Should be 3.9+
   node --version     # Should be 18+
   npm --version      # Should be 9+
   ```

3. **Check the logs**:
   - Backend: Look for errors in Terminal 1
   - Frontend: Look for errors in Terminal 2
   - Browser Console: Press F12, check Console tab

## 💡 Tips for Development

1. **Keep both terminals open** - You need backend and frontend running
2. **Use separate browser windows** - One for app, one for docs
3. **Check the browser console** - Many errors show there (F12)
4. **Read error messages carefully** - They usually tell you what's wrong
5. **Restart when stuck** - Often fixes mysterious issues

## 📞 Getting Help

If you're stuck:

1. **Check the documentation**:
   - [README.md](README.md) - Setup and API docs
   - [TESTING.md](TESTING.md) - Testing procedures
   - [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide

2. **Common issues**:
   - Most problems are missing dependencies or wrong environment variables
   - Check `.env` files are created and filled in
   - Verify Python and Node versions

3. **Still stuck?**:
   - Review the error message
   - Search for the error online
   - Check the relevant documentation section

## ✅ Verification Checklist

After following this guide, you should have:

- [x] Backend running on port 8000
- [x] Frontend running on port 3000
- [x] Ability to create accounts
- [x] Ability to generate exams
- [x] Ability to upload files
- [x] All features accessible in the UI

## 🚀 You're Ready!

You now have a fully functional AI Study Assistant. Start exploring the features and building amazing study experiences!

---

**Happy Learning! 📚✨**
