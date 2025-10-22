# 🌐 Free Hosting Guide - Carbon DNA Ledger

## 🎯 **3 FREE Hosting Options (No Credit Card Required)**

---

## ✨ **Option 1: Streamlit Community Cloud (EASIEST - Recommended for Demo)**

### **Best For:** Quick demos, Streamlit-focused apps
### **Free Tier:** Unlimited public apps, 1GB RAM, 1 CPU
### **URL Example:** `https://carbon-dna-ledger.streamlit.app`

### **Steps:**

#### 1. Prepare Your Repository
Your code is already on GitHub ✅

#### 2. Sign Up for Streamlit Cloud
- Go to: https://share.streamlit.io/
- Click "Sign up" and connect your GitHub account
- Authorize Streamlit to access your repositories

#### 3. Deploy Your App
1. Click "New app"
2. Select repository: `Prabin-Giri/carbon-dna-ledger`
3. Set branch: `main`
4. Main file path: `ui/app.py`
5. Click "Advanced settings"

#### 4. Add Environment Variables (Secrets)
```toml
# In Streamlit Cloud secrets:
DATABASE_URL = "postgresql://postgres:Nischita%409@db.mfegdhndowdtphrqazrl.supabase.co:5432/postgres"
API_BASE = "http://127.0.0.1:8000"
COMPLIANCE_CT_ENABLED = "true"
```

#### 5. Deploy!
- Click "Deploy"
- Wait 3-5 minutes for build
- Your app will be live at: `https://[your-app-name].streamlit.app`

### **Pros:**
✅ Easiest setup (5 minutes)
✅ Auto-deploys on git push
✅ Built for Streamlit apps
✅ Great for demos and presentations
✅ Free SSL certificate

### **Cons:**
⚠️ Apps go to sleep after inactivity (30 min startup on first visit)
⚠️ Limited to 1GB RAM
⚠️ FastAPI backend needs separate hosting or embedded

---

## 🚀 **Option 2: Render (BEST FOR FULL-STACK)**

### **Best For:** Full production apps with backend + frontend
### **Free Tier:** 750 hours/month, auto-sleep after inactivity
### **URL Example:** `https://carbon-dna-ui.onrender.com`

### **Steps:**

#### 1. Sign Up for Render
- Go to: https://render.com
- Click "Get Started for Free"
- Sign up with GitHub account

#### 2. Deploy Using Blueprint (Easiest)
1. Click "New +" → "Blueprint"
2. Connect your GitHub repository: `Prabin-Giri/carbon-dna-ledger`
3. Render will detect `render.yaml` automatically
4. Click "Apply"

#### 3. Add Environment Variables
For both services (API and UI):
```
DATABASE_URL=postgresql://postgres:Nischita%409@db.mfegdhndowdtphrqazrl.supabase.co:5432/postgres
COMPLIANCE_CT_ENABLED=true
OPENAI_API_KEY=your_key_here (optional)
```

#### 4. Deploy!
- Wait 5-10 minutes for build
- You'll get TWO URLs:
  - API: `https://carbon-dna-api.onrender.com`
  - UI: `https://carbon-dna-ui.onrender.com`

### **Manual Setup (Alternative):**
1. **Deploy API:**
   - New → Web Service
   - Connect repository
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

2. **Deploy UI:**
   - New → Web Service
   - Connect repository
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `streamlit run ui/app.py --server.port $PORT --server.address 0.0.0.0`
   - Add environment variable: `API_BASE=https://carbon-dna-api.onrender.com`

### **Pros:**
✅ Full-stack support (backend + frontend)
✅ Automatic HTTPS
✅ Easy deployment from GitHub
✅ Auto-redeploy on git push
✅ Better performance than Streamlit Cloud

### **Cons:**
⚠️ Apps sleep after 15 min of inactivity (slower cold start)
⚠️ Free tier limited to 750 hours/month
⚠️ Build times can be 5-10 minutes

---

## ⚡ **Option 3: Railway (FAST & MODERN)**

### **Best For:** Modern deployment, great DX
### **Free Tier:** $5 credit/month, no credit card needed initially
### **URL Example:** `https://carbon-dna-ledger.up.railway.app`

### **Steps:**

#### 1. Sign Up for Railway
- Go to: https://railway.app
- Click "Login with GitHub"
- Authorize Railway

#### 2. Deploy from GitHub
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose: `Prabin-Giri/carbon-dna-ledger`
4. Railway auto-detects Python

#### 3. Configure Services

**For API Service:**
1. Go to Settings → Environment
2. Add variables:
```
DATABASE_URL=postgresql://postgres:Nischita%409@db.mfegdhndowdtphrqazrl.supabase.co:5432/postgres
COMPLIANCE_CT_ENABLED=true
PORT=8000
```
3. Settings → Deploy → Start Command:
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**For UI Service (Add New Service):**
1. Add service from same repo
2. Add variables:
```
API_BASE=https://[your-api-url].railway.app
PORT=8501
```
3. Start Command:
```
streamlit run ui/app.py --server.port $PORT --server.address 0.0.0.0
```

#### 4. Generate Domain
- Settings → Networking → Generate Domain
- Your app will be live!

### **Pros:**
✅ Very fast deployment (2-3 minutes)
✅ No sleep mode (always active)
✅ Modern interface and great DX
✅ PostgreSQL database included
✅ Auto-deploys on git push

### **Cons:**
⚠️ $5/month credit limit (good for 1 month free)
⚠️ Need credit card after trial period
⚠️ May need paid plan for production use

---

## 🆓 **Other Free Options:**

### **4. Vercel (Frontend Only)**
- Best for: Streamlit UI only
- URL: `https://carbon-dna.vercel.app`
- Steps: Connect GitHub → Deploy
- **Limitation:** Can't run FastAPI backend

### **5. Heroku (With Eco Plan)**
- Best for: Full apps with database
- Free tier ended, but cheap Eco plan ($5/month)
- Steps: `git push heroku main`
- **Note:** No longer free, but still affordable

### **6. PythonAnywhere**
- Best for: Simple Python apps
- Free tier: Limited CPU/bandwidth
- URL: `https://username.pythonanywhere.com`
- **Limitation:** Complex setup for modern frameworks

---

## 🎯 **RECOMMENDED APPROACH FOR YOUR DEVDAYS DEMO:**

### **Best Strategy: Streamlit Cloud (UI) + Render/Railway (API)**

#### **Why This Works:**
- ✅ Streamlit Cloud: Perfect for showcasing the UI
- ✅ Render/Railway: Handles the FastAPI backend
- ✅ Both completely free
- ✅ Professional URLs for presentation
- ✅ Auto-deploys when you push updates

#### **Quick Setup (15 minutes):**

1. **Deploy API to Render:**
   ```bash
   # Render will detect your repo automatically
   # Just add DATABASE_URL environment variable
   ```
   - URL: `https://carbon-dna-api.onrender.com`

2. **Deploy UI to Streamlit Cloud:**
   ```bash
   # Point API_BASE to Render URL
   API_BASE = "https://carbon-dna-api.onrender.com"
   ```
   - URL: `https://carbon-dna-ledger.streamlit.app`

3. **Share Your Demo Link:**
   ```
   🌐 Live Demo: https://carbon-dna-ledger.streamlit.app
   📚 API Docs: https://carbon-dna-api.onrender.com/docs
   ```

---

## 📋 **Pre-Deployment Checklist:**

### **Before You Deploy:**
- ✅ Code pushed to GitHub
- ✅ `requirements.txt` updated
- ✅ Environment variables ready
- ✅ Supabase database accessible from public internet
- ✅ `.gitignore` includes `.env` (don't commit secrets!)

### **Environment Variables You'll Need:**
```
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres
COMPLIANCE_CT_ENABLED=true
API_BASE=https://your-api-url.onrender.com
```

---

## 🔧 **Troubleshooting Free Hosting:**

### **Common Issues:**

#### **1. "App is sleeping" / Slow first load**
- **Solution:** Free tiers sleep after inactivity (15-30 min)
- **Workaround:** Use UptimeRobot (free) to ping your app every 5 minutes
- **Link:** https://uptimerobot.com

#### **2. "Build failed" / Dependencies error**
- **Solution:** Ensure `requirements.txt` is complete
- **Check:** `runtime.txt` specifies Python 3.11.7

#### **3. "Port binding failed"**
- **Solution:** Use `$PORT` environment variable (not hardcoded 8000/8501)
- **Fix:** 
  ```python
  # Backend
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  
  # Frontend
  streamlit run ui/app.py --server.port $PORT
  ```

#### **4. "Database connection failed"**
- **Solution:** Ensure Supabase allows connections from 0.0.0.0/0
- **Check:** Supabase Project Settings → Database → Connection Pooling

#### **5. "App crashes after deployment"**
- **Solution:** Check logs in hosting platform
- **Common fix:** Missing environment variables

---

## 🚀 **Deploy NOW (Step-by-Step):**

### **FASTEST PATH: Streamlit Cloud (5 Minutes)**

```bash
# 1. Ensure code is on GitHub (DONE ✅)

# 2. Go to https://share.streamlit.io/

# 3. Click "New app"

# 4. Select:
#    - Repository: Prabin-Giri/carbon-dna-ledger
#    - Branch: main
#    - Main file: ui/app.py

# 5. Add secrets (click "Advanced settings"):
DATABASE_URL = "postgresql://postgres:Nischita%409@db.mfegdhndowdtphrqazrl.supabase.co:5432/postgres"
API_BASE = "http://127.0.0.1:8000"
COMPLIANCE_CT_ENABLED = "true"

# 6. Click "Deploy"

# 7. Wait 3-5 minutes

# 8. DONE! Share your link:
#    https://carbon-dna-ledger.streamlit.app
```

---

## 📊 **Comparison Table:**

| Platform | Setup Time | Performance | Sleep Mode | Database | Best For |
|----------|-----------|-------------|------------|----------|----------|
| **Streamlit Cloud** | 5 min | Medium | Yes (30min) | No | Quick demos |
| **Render** | 10 min | Good | Yes (15min) | Yes | Full-stack |
| **Railway** | 8 min | Excellent | No | Yes | Production-like |
| **Vercel** | 5 min | Excellent | No | No | Frontend only |
| **Heroku** | 15 min | Good | Paid only | Yes | Legacy apps |

---

## 🎁 **Bonus: Keep Your App Awake (Free)**

### **UptimeRobot Setup (Prevents Sleep):**

1. Go to: https://uptimerobot.com
2. Sign up (free)
3. Add new monitor:
   - Type: HTTP(s)
   - URL: Your deployed app URL
   - Interval: 5 minutes
4. Done! Your app will never sleep

---

## 📱 **After Deployment:**

### **Share Your DevDays Demo:**
```
🌟 Carbon DNA Ledger - Live Demo
🌐 Application: https://carbon-dna-ledger.streamlit.app
📚 API Documentation: https://carbon-dna-api.onrender.com/docs
💻 Source Code: https://github.com/Prabin-Giri/carbon-dna-ledger
📖 Deployment Guide: See FREE_HOSTING_GUIDE.md
```

### **Update Your README:**
Add badges and live demo link to your GitHub README!

```markdown
[![Live Demo](https://img.shields.io/badge/Demo-Live-success)](https://carbon-dna-ledger.streamlit.app)
[![API](https://img.shields.io/badge/API-Docs-blue)](https://carbon-dna-api.onrender.com/docs)
```

---

## 💡 **Pro Tips:**

1. **Always use HTTPS** for production URLs
2. **Monitor your usage** on free tiers
3. **Enable auto-deploy** on git push
4. **Use environment variables** for secrets
5. **Test locally first** before deploying
6. **Check platform status** if deployment fails
7. **Read platform logs** for debugging

---

## ✅ **Your App is Free-Hosting Ready!**

All necessary files are already in your repository:
- ✅ `Dockerfile` - Container deployment
- ✅ `render.yaml` - Render blueprint
- ✅ `railway.json` - Railway config
- ✅ `Procfile` - Heroku config
- ✅ `runtime.txt` - Python version
- ✅ `.streamlit/config.toml` - Streamlit settings
- ✅ `requirements.txt` - Dependencies

**Just push to GitHub and deploy! 🚀**

---

**Last Updated:** October 22, 2025  
**Status:** ✅ Ready for Deployment  
**Estimated Setup Time:** 5-15 minutes depending on platform

