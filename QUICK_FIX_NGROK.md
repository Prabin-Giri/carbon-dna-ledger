# ⚡ QUICK FIX: Expose Local Backend with ngrok (5 minutes)

## 🎯 **Use This If You Need Your Demo Working RIGHT NOW!**

### **Step 1: Start Your Local Backend** (1 minute)

Open a terminal and run:
```bash
cd /Users/bipinsapkota/Downloads/CarbonDNAReport
export DATABASE_URL="postgresql://postgres:Nischita%409@db.mfegdhndowdtphrqazrl.supabase.co:5432/postgres"
export COMPLIANCE_CT_ENABLED=true
export OPENAI_API_KEY="sk-proj-your-actual-key"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Wait until you see: `Application startup complete`

### **Step 2: Install ngrok** (2 minutes)

```bash
# On macOS (with Homebrew)
brew install ngrok

# Or download from: https://ngrok.com/download
```

Sign up for free account at: https://ngrok.com/signup

### **Step 3: Expose Your Backend** (1 minute)

In a **NEW terminal**:
```bash
ngrok http 8000
```

You'll see output like:
```
Forwarding   https://abc123.ngrok.io -> http://localhost:8000
```

**Copy that HTTPS URL!** (e.g., `https://abc123.ngrok.io`)

### **Step 4: Update Streamlit Cloud Secrets** (1 minute)

1. Go to your Streamlit Cloud app
2. Click "⋮" → "Settings" → "Secrets"
3. **Update API_BASE:**
   ```toml
   DATABASE_URL = "postgresql://postgres:Nischita%409@db.mfegdhndowdtphrqazrl.supabase.co:5432/postgres"
   COMPLIANCE_CT_ENABLED = "true"
   OPENAI_API_KEY = "sk-proj-your-key"
   API_BASE = "https://abc123.ngrok.io"  # ← YOUR NGROK URL
   ```
4. Save

### **Step 5: Test!**

Wait 1-2 minutes, refresh your Streamlit Cloud app - **IT WORKS!** ✅

### **⚠️ Important:**
- Keep your terminal running!
- Keep ngrok running!
- This works for demos but NOT production
- For production, use Render deployment

---

## ✅ **Pros:**
- ✅ Works in 5 minutes
- ✅ No cloud deployment needed
- ✅ Perfect for quick demos
- ✅ Free

## ❌ **Cons:**
- ❌ Must keep computer running
- ❌ Must keep terminal open
- ❌ ngrok URL changes if you restart
- ❌ Not suitable for long-term hosting

---

**Use this for DevDays demo if you need it working IMMEDIATELY!**

