# Production Deployment Guide

This guide covers deploying the AI Study Assistant to production environments.

## Table of Contents
- [Backend Deployment](#backend-deployment)
- [Frontend Deployment](#frontend-deployment)
- [Database Setup](#database-setup)
- [Environment Variables](#environment-variables)
- [Stripe Configuration](#stripe-configuration)
- [Monitoring & Maintenance](#monitoring--maintenance)

## Backend Deployment

### Recommended Platforms
- Railway (easiest)
- Render
- Fly.io
- AWS EC2 / DigitalOcean

### Railway Deployment

1. **Create New Project**
   ```bash
   railway login
   railway init
   ```

2. **Add PostgreSQL**
   ```bash
   railway add postgresql
   ```

3. **Set Environment Variables**
   ```bash
   railway variables set OPENAI_API_KEY="sk-proj-..."
   railway variables set JWT_SECRET_KEY="your-random-secret"
   railway variables set STRIPE_SECRET_KEY="sk_live_..."
   railway variables set STRIPE_WEBHOOK_SECRET="whsec_..."
   ```

4. **Update Database Connection**
   In `main.py`, update database URL:
   ```python
   import os
   DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./study_assistant.db")
   # Railway provides DATABASE_URL automatically
   ```

5. **Deploy**
   ```bash
   railway up
   ```

### Render Deployment

1. **Create `render.yaml`**
   ```yaml
   services:
     - type: web
       name: ai-study-assistant-backend
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
       envVars:
         - key: OPENAI_API_KEY
           sync: false
         - key: JWT_SECRET_KEY
           generateValue: true
         - key: STRIPE_SECRET_KEY
           sync: false
         - key: STRIPE_WEBHOOK_SECRET
           sync: false
   
   databases:
     - name: study-assistant-db
       databaseName: study_assistant
       user: study_user
   ```

2. **Push to GitHub and connect to Render**

### Docker Deployment

**Dockerfile (backend)**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and Run**
```bash
docker build -t ai-study-backend .
docker run -p 8000:8000 --env-file .env ai-study-backend
```

## Frontend Deployment

### Vercel Deployment (Recommended)

1. **Install Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **Login and Deploy**
   ```bash
   cd frontend
   vercel login
   vercel
   ```

3. **Set Environment Variables** (in Vercel Dashboard)
   - `BACKEND_BASE`: Your backend URL (e.g., `https://api.yourdomain.com`)
   - `NEXT_PUBLIC_API_BASE`: `/api`
   - `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`: `pk_live_...`

4. **Production Deploy**
   ```bash
   vercel --prod
   ```

### Netlify Deployment

1. **Create `netlify.toml`**
   ```toml
   [build]
     command = "npm run build"
     publish = ".next"
   
   [[redirects]]
     from = "/api/*"
     to = "https://your-backend-url.com/:splat"
     status = 200
   ```

2. **Deploy via CLI or GitHub**
   ```bash
   netlify deploy --prod
   ```

## Database Setup

### Migrating from SQLite to PostgreSQL

1. **Update Database URL**
   ```python
   # In main.py
   DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./study_assistant.db")
   
   # PostgreSQL URLs need special handling
   if DATABASE_URL.startswith("postgres://"):
       DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
   ```

2. **Install PostgreSQL Driver**
   ```bash
   pip install psycopg2-binary
   ```

3. **Update requirements.txt**
   ```
   psycopg2-binary==2.9.9
   ```

4. **Create Tables**
   Tables will be created automatically on first run due to:
   ```python
   Base.metadata.create_all(bind=engine)
   ```

### Database Backup (PostgreSQL)

```bash
# Backup
pg_dump -h localhost -U user -d study_assistant > backup.sql

# Restore
psql -h localhost -U user -d study_assistant < backup.sql
```

## Environment Variables

### Backend Production Variables

```bash
# Required
OPENAI_API_KEY=sk-proj-...
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Optional (for Stripe)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_MONTHLY=price_...

# Optional (for production settings)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Frontend Production Variables

```bash
# Required
BACKEND_BASE=https://api.yourdomain.com
NEXT_PUBLIC_API_BASE=/api

# Optional (for Stripe)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
```

### Generating Secrets

```bash
# JWT Secret
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Stripe Configuration

### 1. Create Products & Prices

1. **Go to Stripe Dashboard** → Products
2. **Create Product**: "Premium Subscription"
3. **Add Price**: $9.99/month recurring
4. **Copy Price ID**: `price_...`

### 2. Set Up Webhook

1. **Go to Stripe Dashboard** → Developers → Webhooks
2. **Add Endpoint**: `https://api.yourdomain.com/billing/webhook`
3. **Select Events**: `checkout.session.completed`
4. **Copy Webhook Secret**: `whsec_...`

### 3. Update Environment Variables

```bash
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_MONTHLY=price_...
```

### 4. Test Webhook

```bash
stripe trigger checkout.session.completed
```

## Security Checklist

- [ ] Use HTTPS in production
- [ ] Restrict CORS origins to your domain
- [ ] Use strong JWT secret (32+ chars)
- [ ] Enable Stripe webhook signature verification
- [ ] Use environment variables for all secrets
- [ ] Never commit .env files
- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable rate limiting (consider Redis)
- [ ] Set up proper logging
- [ ] Configure firewall rules
- [ ] Regular security updates

## CORS Configuration

Update `main.py` for production:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://www.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Monitoring & Maintenance

### Logging

Add structured logging:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@app.post("/upload")
async def upload_files(...):
    logger.info(f"User {current_user.id} uploading {len(files)} files")
    # ... rest of code
```

### Health Monitoring

Use the `/health` endpoint with:
- UptimeRobot
- Pingdom
- Custom monitoring service

```bash
curl https://api.yourdomain.com/health
```

### Database Backups

**Automated Backups (Render/Railway)**
- Enable automatic daily backups in dashboard

**Manual Backups**
```bash
# PostgreSQL
pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql

# Upload to S3
aws s3 cp backup-$(date +%Y%m%d).sql s3://your-bucket/backups/
```

### Performance Optimization

1. **Add Redis for Rate Limiting**
   ```python
   import redis
   r = redis.from_url(os.getenv("REDIS_URL"))
   ```

2. **Enable Response Caching**
   ```python
   from fastapi_cache import FastAPICache
   from fastapi_cache.backends.redis import RedisBackend
   
   @app.on_event("startup")
   async def startup():
       FastAPICache.init(RedisBackend(r), prefix="fastapi-cache")
   ```

3. **Use CDN for Frontend** (Vercel includes this)

### Scaling

**Horizontal Scaling**
- Use load balancer (e.g., Nginx, AWS ALB)
- Deploy multiple backend instances
- Share Redis for rate limiting
- Use external database (PostgreSQL)

**Vertical Scaling**
- Increase server resources
- Optimize database queries
- Add database indexes

## Troubleshooting

### CORS Errors
- Verify `allow_origins` includes frontend domain
- Check `allow_credentials=True`

### Database Connection Issues
- Verify `DATABASE_URL` format
- Check firewall/security groups
- Ensure SSL mode if required

### Stripe Webhook Failures
- Verify webhook URL is accessible
- Check signature verification
- Review Stripe dashboard for errors

### OpenAI API Errors
- Check API key validity
- Monitor rate limits
- Review billing/quota

## Cost Estimation

**Monthly Costs (estimated)**
- Backend hosting (Railway/Render): $5-20
- Database (PostgreSQL): $5-15
- Frontend hosting (Vercel): Free-$20
- OpenAI API: Variable (pay-per-use)
- Stripe: 2.9% + $0.30 per transaction

**Total**: ~$15-50/month + usage costs

## Support & Resources

- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
- [Stripe Integration](https://stripe.com/docs/payments/checkout)
- [Railway Documentation](https://docs.railway.app/)
- [Vercel Documentation](https://vercel.com/docs)
