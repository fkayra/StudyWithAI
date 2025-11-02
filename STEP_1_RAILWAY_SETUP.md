# 🚀 Step 1: Production Setup with Railway

This is THE MOST IMPORTANT first step before launching to production.

## Why Railway?

- ✅ Easiest setup among all platforms
- ✅ Managed PostgreSQL included
- ✅ Auto-deployment from GitHub
- ✅ Free $5 credit (then ~$10-20/month)
- ✅ HTTPS automatic
- ✅ Environment variables management
- ✅ Built-in monitoring

## Time Required: 30-60 minutes

---

## Part 1: Prepare Your Code (15 minutes)

### 1. Update requirements.txt

Add PostgreSQL driver:

```bash
cd backend
```

Edit `requirements.txt`, add this line:
```
psycopg2-binary==2.9.9
```

Or run:
```bash
echo "psycopg2-binary==2.9.9" >> requirements.txt
```

### 2. Update main.py for PostgreSQL

Open `backend/main.py`, find this line (~line 34):
```python
DATABASE_URL = "sqlite:///./study_assistant.db"
```

Change to:
```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./study_assistant.db")
```

This allows Railway to inject PostgreSQL URL while keeping SQLite for local dev.

### 3. Fix SQLAlchemy for PostgreSQL

Find this line (~line 55):
```python
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
```

Change to:
```python
# check_same_thread is only for SQLite
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)
```

### 4. Create Procfile for Railway

Create a new file `backend/Procfile`:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 5. Create runtime.txt (specify Python version)

Create `backend/runtime.txt`:
```
python-3.11
```

### 6. Commit changes

```bash
git add -A
git commit -m "Prepare backend for Railway deployment with PostgreSQL"
git push
```

---

## Part 2: Set Up Railway (15 minutes)

### 1. Create Railway Account

1. Go to https://railway.app/
2. Click "Login" → Sign in with GitHub
3. Authorize Railway to access your repos

### 2. Create New Project

1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your `StudyWithAI` repository
4. Select the `cursor/handle-api-internal-server-error-876c` branch

### 3. Configure Root Directory

1. Railway will detect your repo
2. Click on the service → Settings
3. Find "Root Directory"
4. Set it to: `backend`
5. Click "Save"

### 4. Add PostgreSQL Database

1. Click "+ New" in your project
2. Select "Database" → "PostgreSQL"
3. Railway will create a managed PostgreSQL instance
4. Wait 1-2 minutes for it to provision

### 5. Link Database to Backend

1. Click on your backend service
2. Go to "Variables" tab
3. Click "Reference" dropdown
4. Select your PostgreSQL database
5. Choose `DATABASE_URL`
6. This automatically connects your backend to database

---

## Part 3: Configure Environment Variables (10 minutes)

In your backend service on Railway, go to "Variables" tab and add:

### Required Variables:

```bash
# OpenAI API Key (REQUIRED)
OPENAI_API_KEY=sk-proj-your-actual-key-here

# JWT Secret (Generate a strong one)
JWT_SECRET_KEY=your-super-secret-random-string-here

# CORS Origins (Your frontend URL - will add later)
CORS_ORIGINS=https://your-frontend-url.vercel.app

# Database URL (Already added by Railway)
DATABASE_URL=postgresql://... (auto-added)

# Port (Railway provides this automatically)
PORT=8000
```

### How to Generate JWT Secret:

**Option 1 - Python:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Option 2 - OpenSSL:**
```bash
openssl rand -base64 32
```

**Option 3 - Online:**
Go to https://randomkeygen.com/ and copy a "CodeIgniter Encryption Key"

### Optional but Recommended:

```bash
# Stripe (if using payments)
STRIPE_SECRET_KEY=sk_test_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

---

## Part 4: Deploy Backend (5 minutes)

1. After adding all variables, click "Deploy"
2. Railway will:
   - Install dependencies
   - Start your application
   - Create PostgreSQL tables
   - Generate a public URL

3. Wait 2-5 minutes for deployment

4. Once deployed, you'll see a URL like:
   ```
   https://your-app-name.up.railway.app
   ```

5. Test it by visiting:
   ```
   https://your-app-name.up.railway.app/health
   ```

   You should see:
   ```json
   {"status": "healthy", "database": "connected"}
   ```

---

## Part 5: Deploy Frontend to Vercel (10 minutes)

### 1. Create Vercel Account

1. Go to https://vercel.com/
2. Sign in with GitHub
3. Click "Add New" → "Project"

### 2. Import Repository

1. Select your `StudyWithAI` repository
2. Vercel will detect it's a Next.js app
3. Configure:
   - **Framework Preset:** Next.js
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build` (default)
   - **Output Directory:** `.next` (default)

### 3. Add Environment Variable

Before deploying, add this environment variable:

```bash
NEXT_PUBLIC_API_BASE=https://your-app-name.up.railway.app
```

(Use the Railway URL from Part 4)

### 4. Deploy

1. Click "Deploy"
2. Wait 2-3 minutes
3. You'll get a URL like: `https://your-app.vercel.app`

### 5. Update CORS in Railway

1. Go back to Railway
2. Open your backend service
3. Go to Variables
4. Update `CORS_ORIGINS`:
   ```
   CORS_ORIGINS=https://your-app.vercel.app
   ```
5. Railway will auto-redeploy (takes 1-2 minutes)

---

## Part 6: Verify Everything Works (5 minutes)

### Test Checklist:

1. **Backend Health:**
   - Visit: `https://your-backend.up.railway.app/health`
   - Should see: `{"status": "healthy", "database": "connected"}`

2. **Frontend:**
   - Visit: `https://your-app.vercel.app`
   - Should see your homepage

3. **Registration:**
   - Click "Get Started" or go to `/register`
   - Create a test account
   - Should redirect to dashboard

4. **File Upload:**
   - Go to Upload page
   - Upload a test document
   - Should work without errors

5. **Generate Content:**
   - Try generating a summary
   - Try generating flashcards
   - Try generating an exam

---

## 🎉 Success! You're Now in Production

Your app is now:
- ✅ Running on production infrastructure
- ✅ Using PostgreSQL (not SQLite)
- ✅ Accessible from anywhere in the world
- ✅ Has HTTPS enabled
- ✅ Auto-deploys on git push

---

## 💰 Expected Costs

**Railway (Backend + Database):**
- Free $5 credit included
- After credit: ~$10-20/month
- Scales with usage

**Vercel (Frontend):**
- Free tier: Perfect for starting
- Hobby: $20/month (when you scale)

**Total to start:** $0 (using free credits)  
**After free tier:** $10-20/month

---

## 🔄 Auto-Deployment

Now, every time you push to GitHub:
- Railway auto-deploys backend
- Vercel auto-deploys frontend

Just:
```bash
git add .
git commit -m "Your changes"
git push
```

And your live site updates in 2-3 minutes! 🚀

---

## 🐛 Troubleshooting

### "Application failed to respond"
- Check Railway logs (click service → Deployments → View Logs)
- Verify `PORT` environment variable exists
- Make sure `Procfile` is correct

### "Database connection error"
- Verify `DATABASE_URL` is set in Railway
- Check if PostgreSQL service is running
- Look at deployment logs for errors

### "CORS error" on frontend
- Make sure `CORS_ORIGINS` includes your Vercel URL
- No trailing slash in URL
- Railway redeployed after changing env vars

### Frontend can't connect to backend
- Check `NEXT_PUBLIC_API_BASE` in Vercel
- Verify Railway backend is responding at `/health`
- Check browser console for exact error

---

## 📊 Monitoring

### Railway Dashboard:
- View logs in real-time
- Monitor CPU/Memory usage
- See deployment history
- Check database metrics

### Vercel Dashboard:
- View deployment status
- Monitor frontend performance
- See visitor analytics
- Check build logs

---

## 🔐 Security Notes

After deploying:
1. ✅ Change JWT_SECRET_KEY to a strong random string
2. ✅ Set specific CORS_ORIGINS (not *)
3. ✅ Keep OPENAI_API_KEY secret
4. ✅ HTTPS is automatic (both Railway and Vercel)

---

## 📝 What to Do Next

After completing Step 1, you have a working production environment!

**Immediate next steps:**

1. **Add Monitoring** (Step 2)
   - Set up Sentry for error tracking
   - Add usage analytics

2. **Test with Real Users** (Step 3)
   - Invite 5-10 beta testers
   - Collect feedback
   - Fix critical bugs

3. **Optimize** (Step 4)
   - Add Redis for caching (Railway has it!)
   - Implement file storage (S3 or R2)
   - Add rate limiting

But for now, **congratulations!** 🎉  
You've completed the most important step!

---

## 🆘 Need Help?

- Railway Docs: https://docs.railway.app/
- Vercel Docs: https://vercel.com/docs
- Railway Discord: https://discord.gg/railway
- Your app is now production-ready for initial testing! 🚀
