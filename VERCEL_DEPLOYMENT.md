# Vercel Deployment Rehberi

Bu rehber, AI Study Assistant uygulamasının Vercel'e nasıl deploy edileceğini adım adım açıklar.

## Genel Bakış

Projemizde:
- **Frontend**: Next.js (Vercel'de host edilecek)
- **Backend**: FastAPI (Railway, Render veya başka bir platformda host edilmeli)

## Önkoşullar

✅ Backend'iniz bir platformda yayında olmalı (Railway, Render, Fly.io, vb.)
✅ Backend URL'inizi bilmelisiniz (örn: `https://your-backend.railway.app`)
✅ Vercel hesabınız olmalı

## Adım 1: Backend Deployment

**Backend'i önce deploy edin!** Frontend backend'e bağlanacağı için backend URL'sine ihtiyacınız var.

### Önerilen Backend Platformları:
- **Railway** (Kolay, otomatik SSL)
- **Render** (Ücretsiz plan var)
- **Fly.io** (Global deployment)

### Backend Environment Variables

Backend platformunuzda şu environment variables'ları ayarlayın:

```bash
# ZORUNLU
OPENAI_API_KEY=sk-proj-xxx...
JWT_SECRET_KEY=your-secret-key-min-32-chars
DATABASE_URL=postgresql://...  # Platform otomatik sağlar (Railway/Render)

# İSTEĞE BAĞLI (Stripe kullanıyorsanız)
STRIPE_SECRET_KEY=sk_live_xxx...
STRIPE_WEBHOOK_SECRET=whsec_xxx...

# İSTEĞE BAĞLI (CORS için)
CORS_ORIGINS=https://your-app.vercel.app,https://www.your-app.vercel.app
```

**Not:** Backend'de CORS_ORIGINS ayarlanmazsa, production'da tüm origin'lere izin verilir (development kolaylığı için).

## Adım 2: Vercel'e Frontend Deploy Etme

### Seçenek A: Vercel Dashboard Üzerinden (Kolay)

1. **Vercel'e giriş yapın**: https://vercel.com/login

2. **New Project** butonuna tıklayın

3. **Git repository'nizi import edin**
   - GitHub, GitLab veya Bitbucket'tan repository'nizi seçin
   - Deploy edilecek branch'i seçin (örn: `main` veya `cursor/fix-vercel-deployment-configuration-950b`)

4. **Build & Development Settings**
   - Framework Preset: `Next.js`
   - Root Directory: `frontend` (önemli!)
   - Build Command: `npm run build` (otomatik gelir)
   - Output Directory: `.next` (otomatik gelir)

5. **Environment Variables ekleyin**

   **ZORUNLU:**
   ```
   NEXT_PUBLIC_API_URL = https://your-backend.railway.app
   ```

   **İSTEĞE BAĞLI (Stripe kullanıyorsanız):**
   ```
   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY = pk_live_xxx...
   ```

6. **Deploy** butonuna tıklayın

### Seçenek B: Vercel CLI ile (Gelişmiş)

```bash
# Vercel CLI'yi yükleyin
npm i -g vercel

# Frontend klasörüne gidin
cd frontend

# Vercel'e login olun
vercel login

# İlk deployment (development)
vercel

# Environment variables'ları ekleyin (interactive)
vercel env add NEXT_PUBLIC_API_URL

# Production deployment
vercel --prod
```

## Adım 3: Environment Variables Detayları

### Frontend Environment Variables

#### `NEXT_PUBLIC_API_URL` (Zorunlu)

Backend'inizin tam URL'si. **Sonunda `/` olmamalı!**

```bash
# DOĞRU
NEXT_PUBLIC_API_URL=https://your-backend.railway.app

# YANLIŞ
NEXT_PUBLIC_API_URL=https://your-backend.railway.app/
NEXT_PUBLIC_API_URL=localhost:8000
```

**Backend URL nasıl bulunur?**
- **Railway**: Dashboard → Project → Settings → Domains
- **Render**: Dashboard → Service → URL en üstte görünür
- **Fly.io**: `fly info` komutu veya dashboard

#### `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` (İsteğe Bağlı)

Stripe entegrasyonu kullanıyorsanız:

```bash
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_xxx...
# veya test için
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxx...
```

Stripe Dashboard → Developers → API keys'den alabilirsiniz.

## Adım 4: Deploy Sonrası Test

1. **Vercel URL'nizi açın** (örn: `https://your-app.vercel.app`)

2. **Health check**
   - Tarayıcı console'u açın (F12)
   - Network tab'ına gidin
   - API çağrılarını kontrol edin

3. **Test edilmesi gerekenler:**
   - ✅ Ana sayfa yükleniyor mu?
   - ✅ Login/Register çalışıyor mu?
   - ✅ File upload çalışıyor mu?
   - ✅ Exam generation çalışıyor mu?

## Sorun Giderme

### Sorun: "Network Error" veya API çağrıları çalışmıyor

**Çözüm 1: Environment Variables'ı kontrol edin**

Vercel Dashboard'da:
1. Project → Settings → Environment Variables
2. `NEXT_PUBLIC_API_URL` değerinin doğru olduğundan emin olun
3. Değer değiştiyse, yeniden deploy edin: `Deployments → ... → Redeploy`

**Çözüm 2: Backend'in çalıştığından emin olun**

```bash
# Backend health check
curl https://your-backend.railway.app/health
# Beklenen çıktı: {"status":"healthy","timestamp":"..."}
```

**Çözüm 3: CORS hatası**

Backend loglarında "CORS" görüyorsanız, backend'de CORS_ORIGINS environment variable'ını ayarlayın:

```bash
CORS_ORIGINS=https://your-app.vercel.app
```

### Sorun: Build hatası

**"Module not found" hatası:**

```bash
cd frontend
npm install
npm run build  # Local'de test edin
```

**"Next.js config" hatası:**

`frontend/next.config.js` dosyasının doğru olduğundan emin olun.

### Sorun: Environment variables güncellenmiyor

Environment variables değiştirdikten sonra **mutlaka yeniden deploy edin**:

1. Vercel Dashboard → Deployments
2. En son deployment → ... → Redeploy

veya CLI ile:
```bash
vercel --prod
```

### Sorun: 500 Internal Server Error

**Backend loglarını kontrol edin:**
- Railway: Dashboard → Deployments → View Logs
- Render: Dashboard → Logs
- Fly.io: `fly logs`

Genellikle sorunlar:
- ❌ OPENAI_API_KEY eksik veya hatalı
- ❌ DATABASE_URL hatalı
- ❌ JWT_SECRET_KEY eksik

## Environment Variables Özet Tablosu

| Platform | Variable | Zorunlu? | Örnek Değer |
|----------|----------|----------|-------------|
| **Vercel (Frontend)** | `NEXT_PUBLIC_API_URL` | ✅ Evet | `https://backend.railway.app` |
| **Vercel (Frontend)** | `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | ❌ Hayır | `pk_live_xxx` |
| **Backend (Railway/Render)** | `OPENAI_API_KEY` | ✅ Evet | `sk-proj-xxx` |
| **Backend** | `JWT_SECRET_KEY` | ✅ Evet | `your-secret-32-chars` |
| **Backend** | `DATABASE_URL` | ✅ Evet | Otomatik (Railway/Render) |
| **Backend** | `CORS_ORIGINS` | ❌ Hayır | `https://app.vercel.app` |
| **Backend** | `STRIPE_SECRET_KEY` | ❌ Hayır | `sk_live_xxx` |
| **Backend** | `STRIPE_WEBHOOK_SECRET` | ❌ Hayır | `whsec_xxx` |

## Custom Domain Ekleme (İsteğe Bağlı)

1. **Vercel Dashboard** → Project → Settings → Domains
2. Domain adınızı ekleyin (örn: `studyapp.com`)
3. DNS ayarlarınızı güncelleyin (Vercel size talimatlar verir)
4. Backend'de CORS_ORIGINS'e yeni domain'i ekleyin:

```bash
CORS_ORIGINS=https://studyapp.com,https://www.studyapp.com
```

## Production Checklist

Deploy etmeden önce kontrol edin:

- [ ] Backend production'da ve çalışıyor
- [ ] Backend health check yanıt veriyor (`/health`)
- [ ] OPENAI_API_KEY ayarlanmış
- [ ] JWT_SECRET_KEY güvenli (32+ karakter)
- [ ] DATABASE_URL PostgreSQL kullanıyor (SQLite değil)
- [ ] Frontend `NEXT_PUBLIC_API_URL` doğru
- [ ] CORS ayarları doğru (spesifik domain'ler)
- [ ] Stripe keys production keys (test değil)
- [ ] Environment variables production environment'ta ayarlı

## Monitoring

### Vercel Analytics

Vercel otomatik olarak şunları sağlar:
- Performance monitoring
- Error tracking
- Deployment logs

**Erişim:** Dashboard → Project → Analytics

### Backend Monitoring

Backend platform loglarını izleyin:
- Railway: Realtime logs
- Render: Log streams
- Fly.io: `fly logs -a your-app`

## Güncelleme ve Re-deployment

### Otomatik Deployment (Git Push)

Vercel otomatik olarak her git push'ta deploy eder:

```bash
git add .
git commit -m "Update feature"
git push origin main  # veya branch'iniz
```

Vercel otomatik olarak:
1. Kodu çeker
2. Build yapar
3. Deploy eder
4. URL güncellenir

### Manuel Deployment

```bash
cd frontend
vercel --prod
```

## Destek ve Kaynaklar

- [Vercel Documentation](https://vercel.com/docs)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
- [Railway Documentation](https://docs.railway.app)
- [Render Documentation](https://render.com/docs)

## Sık Sorulan Sorular

**S: Backend'i de Vercel'de host edebilir miyim?**

Hayır. Vercel Serverless Functions kullanır ve uzun süren FastAPI backend'ler için uygun değil. Backend için Railway, Render veya Fly.io kullanın.

**S: Environment variables'ı nasıl değiştirebilirim?**

Vercel Dashboard → Settings → Environment Variables → Edit → Save → Redeploy

**S: Neden yeniden deploy etmem gerekiyor?**

Environment variables build time'da okunur (`NEXT_PUBLIC_*`). Değişiklikler için rebuild gerekir.

**S: Free tier yeterli mi?**

Evet! Vercel'in free tier'ı çoğu kullanım için yeterli. Backend için Railway/Render'ın free tier'ları da kullanılabilir.

**S: Birden fazla environment (staging, production) kullanabilir miyim?**

Evet! Vercel otomatik olarak:
- `main` branch → Production
- Diğer branch'ler → Preview deployments

Her environment için farklı environment variables ayarlayabilirsiniz.
