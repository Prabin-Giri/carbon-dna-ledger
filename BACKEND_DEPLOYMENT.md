# 🚀 Backend Deployment Guide - FastAPI on Render

## ⚠️ **IMPORTANT: Streamlit Cloud Requires Separate Backend**

Streamlit Cloud **ONLY hosts the frontend (UI)**. You need to deploy the FastAPI backend separately!

---

## 🎯 **Quick Backend Deployment to Render (10 minutes - FREE)**

### **Why Render for Backend?**
- ✅ Free tier available (750 hrs/month)
- ✅ Supports FastAPI/Python
- ✅ Auto-deploys from GitHub
- ✅ Provides public HTTPS URL
- ✅ Perfect for this project!

---

## 🚀 **Step-by-Step Backend Deployment:**

### **Step 1: Go to Render** (1 minute)
1. Open: https://render.com
2. Click "Get Started for Free"
3. Sign up with your GitHub account
4. Authorize Render to access your repositories

### **Step 2: Create New Web Service** (2 minutes)
1. Click "**New +**" button (top right)
2. Select "**Web Service**"
3. Click "**Connect a repository**"
4. Find and select: `Prabin-Giri/carbon-dna-ledger`
5. Click "**Connect**"

### **Step 3: Configure the Service** (3 minutes)

Fill in these settings:

#### **Basic Settings:**
```
Name: carbon-dna-api
Region: Oregon (US West) - or closest to you
Branch: main
Runtime: Python 3
```

#### **Build Command:**
```bash
pip install -r requirements.txt
```

#### **Start Command:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

#### **Instance Type:**
```
Free
```

### **Step 4: Add Environment Variables** (2 minutes)

Click "**Advanced**" and add these environment variables:

```
DATABASE_URL=postgresql://postgres:Nischita%409@db.mfegdhndowdtphrqazrl.supabase.co:5432/postgres
COMPLIANCE_CT_ENABLED=true
OPENAI_API_KEY=sk-proj-your-actual-key-here
```

**Important:** Replace `sk-proj-your-actual-key-here` with your real OpenAI API key!

### **Step 5: Deploy!** (2 minutes)
1. Scroll down and click "**Create Web Service**"
2. Wait 5-10 minutes for initial build
3. Watch the logs for deployment progress
4. When you see "Application startup complete" - it's ready! ✅

### **Step 6: Get Your Backend URL** (30 seconds)
Your backend will be live at:
```
https://carbon-dna-api.onrender.com
```
(Replace with your actual Render URL)

**Test it:**
- API Docs: `https://carbon-dna-api.onrender.com/docs`
- Health Check: `https://carbon-dna-api.onrender.com/health`

---

## 🔗 **Step 7: Connect Frontend to Backend**

### **Update Streamlit Cloud Secrets:**

1. Go to your Streamlit Cloud app
2. Click "⋮" menu → "Settings"
3. Go to "Secrets" section
4. Update with your Render backend URL:

```toml
# Database Connection
DATABASE_URL = "postgresql://postgres:Nischita%409@db.mfegdhndowdtphrqazrl.supabase.co:5432/postgres"

# Climate TRACE Integration
COMPLIANCE_CT_ENABLED = "true"

# OpenAI API Key
OPENAI_API_KEY = "sk-proj-your-actual-key-here"

# Backend API URL (IMPORTANT!)
API_BASE = "https://carbon-dna-api.onrender.com"
```

5. Click "Save"
6. Streamlit will auto-restart (wait 1-2 minutes)
7. Test your app!

---

## ✅ **Verification Checklist:**

After deploying, verify:

### **Backend (Render):**
- [ ] Service is "Live" (green indicator)
- [ ] Can access `/docs` endpoint
- [ ] Can access `/health` endpoint
- [ ] Logs show "Application startup complete"
- [ ] No errors in recent logs

### **Frontend (Streamlit Cloud):**
- [ ] App loads without errors
- [ ] Can see navigation menu
- [ ] Dashboard shows data
- [ ] Real-time monitoring works
- [ ] No "Connection refused" errors

---

## 🎯 **Your Complete Deployment:**

Once both are deployed:

```
Frontend (UI):  https://carbon-dna-ledger.streamlit.app
Backend (API):  https://carbon-dna-api.onrender.com
API Docs:       https://carbon-dna-api.onrender.com/docs
Database:       Supabase PostgreSQL (already set up)
```

**Share these links for DevDays! 🎉**

---

## 💡 **Alternative: Deploy Backend to Railway**

If you prefer Railway over Render:

### **Quick Railway Deployment:**

1. Go to: https://railway.app
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway auto-detects Python
5. Add environment variables:
   ```
   DATABASE_URL=your_supabase_url
   COMPLIANCE_CT_ENABLED=true
   OPENAI_API_KEY=sk-proj-your-key
   PORT=8000
   ```
6. Settings → Deploy → Start Command:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
7. Generate domain in Settings → Networking
8. Use the Railway URL as your `API_BASE`

---

## 🆓 **Cost Breakdown:**

### **Free Tier Limits:**

**Render (Backend):**
- ✅ FREE for 750 hours/month
- ✅ Sleeps after 15 min of inactivity
- ✅ Cold start: 30-60 seconds
- ✅ Enough for DevDays and demos!

**Streamlit Cloud (Frontend):**
- ✅ FREE forever (public apps)
- ✅ Unlimited apps
- ✅ Auto-deploys from GitHub
- ✅ Perfect for presentations!

**Total Monthly Cost: $0** 🎉

---

## 🐛 **Troubleshooting:**

### **Error: "Service failed to start"**
**Solution:**
- Check Render logs for specific error
- Verify `requirements.txt` is complete
- Ensure start command uses `$PORT` not `8000`

### **Error: "Database connection failed"**
**Solution:**
- Verify DATABASE_URL is correct
- Check Supabase project is active
- Ensure URL is URL-encoded (% for special chars)

### **Error: "Application timeout"**
**Solution:**
- Render free tier can be slow on first request
- Wait 30-60 seconds for wake-up
- Use UptimeRobot to keep it awake

### **Frontend shows "Connection refused"**
**Solution:**
- Verify API_BASE in Streamlit secrets
- Check Render backend is "Live"
- Test backend URL in browser: `/docs`
- Ensure CORS is enabled (already configured)

---

## 📊 **Deployment Architecture:**

```
┌─────────────────────────────────────────────┐
│         USER'S BROWSER                       │
│  https://carbon-dna-ledger.streamlit.app    │
└──────────────────┬──────────────────────────┘
                   │
                   ├─► Streamlit Cloud (Frontend)
                   │   - Hosts UI only
                   │   - Displays charts/graphs
                   │   - User interactions
                   │
                   ├─► Render (Backend API)
                   │   - FastAPI server
                   │   - Business logic
                   │   - Data processing
                   │
                   └─► Supabase (Database)
                       - PostgreSQL
                       - Stores emission records
                       - Audit snapshots
```

---

## 🎯 **Pro Tips:**

### **1. Keep Backend Awake:**
Use UptimeRobot (free) to ping your backend every 5 minutes:
- URL: `https://carbon-dna-api.onrender.com/health`
- Prevents cold starts during demos!

### **2. Monitor Backend:**
- Check Render dashboard regularly
- Set up email alerts for failures
- Monitor response times

### **3. For DevDays Demo:**
- Wake up backend 5 minutes before presenting
- Test both frontend and backend URLs
- Have API docs ready: `/docs`
- Show the architecture diagram!

---

## 🚀 **Quick Deploy Commands (Summary):**

### **For Render:**
```bash
# No commands needed!
# Just connect GitHub and configure in UI
# Render handles everything automatically
```

### **For Railway:**
```bash
# No commands needed!
# Just connect GitHub and configure in UI
# Railway handles everything automatically
```

### **Both are "click and deploy"** - no terminal needed! 🎉

---

## ✅ **Success Indicators:**

### **Backend is Working When:**
1. ✅ Render shows "Live" status (green)
2. ✅ `/docs` page loads with API documentation
3. ✅ `/health` returns `{"status": "healthy"}`
4. ✅ Logs show "Application startup complete"
5. ✅ No errors in recent logs

### **Frontend is Connected When:**
1. ✅ Streamlit app loads without errors
2. ✅ Dashboard shows metrics
3. ✅ Can create audit snapshots
4. ✅ Charts and graphs render
5. ✅ No "Connection refused" messages

---

## 🎉 **Once Both Are Deployed:**

You'll have:
- ✅ **Frontend**: Publicly accessible UI
- ✅ **Backend**: Publicly accessible API
- ✅ **Database**: Supabase PostgreSQL
- ✅ **FREE hosting** for everything
- ✅ **Auto-deploys** on git push
- ✅ **HTTPS** on both frontend and backend
- ✅ **DevDays ready!** 🚀

**Your demo links:**
```
🌐 Live App: https://carbon-dna-ledger.streamlit.app
📚 API Docs: https://carbon-dna-api.onrender.com/docs
💻 GitHub:   https://github.com/Prabin-Giri/carbon-dna-ledger
```

---

## 📞 **Need Help?**

**Check these docs:**
- `FREE_HOSTING_GUIDE.md` - Comprehensive hosting guide
- `DEPLOY_NOW.md` - Quick 5-minute deployment
- `STREAMLIT_CLOUD_FIXES.md` - Troubleshooting guide

**Resources:**
- Render Docs: https://render.com/docs
- Streamlit Docs: https://docs.streamlit.io
- FastAPI Docs: https://fastapi.tiangolo.com

---

**Last Updated:** October 22, 2025  
**Deployment Time:** 10-15 minutes total  
**Cost:** $0.00 (FREE)  
**Ready for:** DevDays 2025! 🎯

