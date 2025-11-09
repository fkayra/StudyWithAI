# Vercel Deployment Setup Guide

## Environment Variables Required

To deploy the frontend to Vercel, you need to set the following environment variable:

### 1. Backend API URL

**Variable Name:** `NEXT_PUBLIC_API_URL`

**Value:** Your Railway backend URL (e.g., `https://your-backend.railway.app`)

**How to set it in Vercel:**

1. Go to your Vercel project dashboard
2. Navigate to **Settings** → **Environment Variables**
3. Click **Add New**
4. Add:
   - **Name:** `NEXT_PUBLIC_API_URL`
   - **Value:** `https://your-backend.railway.app` (replace with your actual Railway backend URL)
   - **Environment:** Select all environments (Production, Preview, Development)
5. Click **Save**
6. **Redeploy** your application for the changes to take effect

## Common Issues

### Network Error on Login

If you see a "Network error" when trying to login, it usually means:

1. **NEXT_PUBLIC_API_URL is not set** - The frontend is trying to use `/api` which doesn't exist in production
2. **Backend URL is incorrect** - Double-check your Railway backend URL
3. **CORS issues** - Make sure your Railway backend has CORS configured to allow your Vercel domain

### How to Fix Network Errors

1. **Check Environment Variables:**
   - Go to Vercel Dashboard → Your Project → Settings → Environment Variables
   - Verify `NEXT_PUBLIC_API_URL` is set correctly
   - Make sure it includes `https://` and doesn't have a trailing slash

2. **Verify Backend is Running:**
   - Check your Railway dashboard to ensure the backend is running
   - Test the backend URL directly in your browser: `https://your-backend.railway.app/docs`

3. **Check CORS Configuration:**
   - Your Railway backend should allow requests from your Vercel domain
   - Check `CORS_ORIGINS` environment variable in Railway (or set it to `*` for development)

4. **Redeploy:**
   - After setting environment variables, you must redeploy
   - Go to Vercel Dashboard → Your Project → Deployments
   - Click the three dots on the latest deployment → **Redeploy**

## Testing the Setup

1. After setting `NEXT_PUBLIC_API_URL` and redeploying:
2. Open your Vercel-deployed frontend
3. Open browser console (F12)
4. Look for: `[API] Using API_BASE: https://your-backend.railway.app`
5. If you see a warning about using `/api` in production, the environment variable is not set correctly

## Railway Backend Setup

Make sure your Railway backend has:

1. **CORS configured** to allow your Vercel domain:
   ```bash
   CORS_ORIGINS=https://your-vercel-app.vercel.app,https://your-custom-domain.com
   ```
   Or for development:
   ```bash
   CORS_ORIGINS=*
   ```

2. **DATABASE_URL** set correctly (PostgreSQL connection string)

3. **JWT_SECRET_KEY** set (for authentication)

4. **Other required environment variables** (OPENAI_API_KEY, STRIPE_SECRET_KEY, etc.)

## Quick Checklist

- [ ] `NEXT_PUBLIC_API_URL` is set in Vercel environment variables
- [ ] Backend URL is correct and accessible
- [ ] Backend is running on Railway
- [ ] CORS is configured in Railway backend
- [ ] Frontend has been redeployed after setting environment variables
- [ ] Test login works on the deployed frontend

