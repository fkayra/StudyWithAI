# ⚡ Vercel'e Deploy - Hızlı Başlangıç

## 🎯 Yapmanız Gerekenler (5 Dakika)

### 1️⃣ Backend Environment Variables'ı Ayarlayın

Backend platformunuzda (Railway/Render/Fly.io) şu değişkenleri ekleyin:

```bash
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
JWT_SECRET_KEY=en-az-32-karakter-rastgele-string
CORS_ORIGINS=*
```

**Backend URL'nizi not alın** (örn: `https://your-backend.railway.app`)

### 2️⃣ Vercel'de Frontend'i Deploy Edin

#### Yöntem 1: Dashboard (Tavsiye Edilen)

1. https://vercel.com → Login
2. **New Project** → GitHub repository'nizi import edin
3. **Root Directory:** `frontend` yazın
4. **Environment Variables** ekleyin:
   ```
   NEXT_PUBLIC_API_URL = https://your-backend.railway.app
   ```
5. **Deploy** butonuna basın

#### Yöntem 2: CLI

```bash
cd frontend
npm i -g vercel
vercel login
vercel env add NEXT_PUBLIC_API_URL  # Backend URL'nizi girin
vercel --prod
```

### 3️⃣ Test Edin

Vercel'in verdiği URL'yi açın ve test edin:
- ✅ Ana sayfa açılıyor mu?
- ✅ Login/Register çalışıyor mu?
- ✅ Console'da (F12) hata var mı?

## 🔧 Sorun mu Yaşıyorsunuz?

### "Network Error" alıyorsanız:

1. **Backend çalışıyor mu?**
   ```bash
   curl https://your-backend.railway.app/health
   ```
   Yanıt: `{"status":"healthy",...}` görmeli

2. **NEXT_PUBLIC_API_URL doğru mu?**
   - Vercel Dashboard → Settings → Environment Variables
   - Değer: `https://your-backend.railway.app` (sonunda `/` yok!)
   - Değiştirdiyseniz: Deployments → Redeploy

3. **Backend CORS ayarları doğru mu?**
   Backend environment variables'a ekleyin:
   ```bash
   CORS_ORIGINS=https://your-app.vercel.app
   ```

### API çağrıları "401 Unauthorized" dönüyorsa:

- Backend'de `JWT_SECRET_KEY` ayarlanmış mı?
- Frontend'de logout/login yapın

### Build hatası alıyorsanız:

```bash
cd frontend
npm install
npm run build  # Local'de test edin
```

## 📚 Detaylı Dokümantasyon

Daha fazla bilgi için: [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md)

## ✅ Production Checklist

Deploy etmeden önce:
- [ ] Backend production'da ve çalışıyor
- [ ] OPENAI_API_KEY ayarlanmış
- [ ] JWT_SECRET_KEY güvenli (32+ karakter)
- [ ] NEXT_PUBLIC_API_URL Vercel'de ayarlı
- [ ] Backend CORS ayarları doğru

## 🆘 Hala Çalışmıyor mu?

1. Backend loglarını kontrol edin (Railway/Render dashboard)
2. Vercel deployment loglarını kontrol edin
3. Browser console'u kontrol edin (F12 → Console)
4. [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md) dosyasındaki "Sorun Giderme" bölümüne bakın
