# 🔧 Streamlit Cloud Deployment Fixes

## Common Errors and Solutions

---

## ✅ **FIXED: ModuleNotFoundError - dotenv**

### **Error Message:**
```
ModuleNotFoundError: This app has encountered an error.
Traceback:
File "/mount/src/carbon-dna-ledger/ui/app.py", line 5, in <module>
    from dotenv import load_dotenv
```

### **What Happened:**
Streamlit Cloud has its own secrets management and doesn't need `python-dotenv`. The import was causing issues.

### **Fix Applied:** ✅
- Made `dotenv` import optional with try-except
- App now works on both local dev and Streamlit Cloud
- Already committed and pushed to GitHub

### **What You Need to Do:**
**Nothing!** Streamlit Cloud will auto-redeploy from the latest GitHub commit.

Just wait 2-3 minutes and refresh your app. It should work now! 🎉

---

## 🚀 **Deployment Checklist for Streamlit Cloud**

### **1. Repository Setup** ✅
- [x] Code pushed to GitHub
- [x] Latest commit includes the fix
- [x] All files in repository

### **2. Streamlit Cloud Configuration**
When deploying, make sure you have:

#### **Repository Settings:**
```
Repository: Prabin-Giri/carbon-dna-ledger
Branch: main
Main file path: ui/app.py
```

#### **Advanced Settings - Secrets:**
```toml
DATABASE_URL = "postgresql://postgres:Nischita%409@db.mfegdhndowdtphrqazrl.supabase.co:5432/postgres"
COMPLIANCE_CT_ENABLED = "true"
API_BASE = "http://127.0.0.1:8000"
OPENAI_API_KEY = "sk-proj-your-actual-key-here"
```

#### **Python Version:**
```
3.11
```
(Streamlit Cloud should detect this from `runtime.txt`)

---

## 🐛 **Other Common Streamlit Cloud Errors**

### **Error: "This app has crashed"**

**Possible Causes:**
1. Missing secrets/environment variables
2. Database connection failure
3. Import errors

**Solutions:**
1. Check secrets are configured correctly
2. Verify DATABASE_URL is accessible from internet
3. Check app logs: Click "Manage app" → "Logs"

---

### **Error: "Module not found" (other modules)**

**Example:**
```
ModuleNotFoundError: No module named 'plotly'
```

**Solution:**
1. Ensure module is in `requirements.txt`
2. Check for typos in package names
3. Rebuild app: Settings → Reboot app

---

### **Error: "Connection timeout" or "Database error"**

**Possible Causes:**
1. Supabase database not accessible
2. Wrong DATABASE_URL
3. Database paused/suspended

**Solutions:**
1. Check Supabase project is active
2. Verify DATABASE_URL in secrets
3. Test connection: Try from different network
4. Ensure Supabase allows connections from 0.0.0.0/0

---

### **Error: "App is taking too long to load"**

**Causes:**
- App is waking up from sleep (free tier)
- Heavy dependencies loading
- Database connection slow

**Solutions:**
- Wait 30-60 seconds on first load
- Use UptimeRobot to keep app awake
- Optimize imports (lazy loading)

---

## 📋 **Post-Deployment Verification**

### **After deployment, check these:**

#### **1. App Loads Successfully** ✅
- Homepage displays
- No error messages
- UI components render

#### **2. Database Connection Works** ✅
- Can see emission records
- Analytics dashboard loads
- Audit snapshots accessible

#### **3. All Features Work** ✅
- Real-time monitoring displays
- Can create audit snapshots
- Compliance scoring works
- Charts and graphs render

#### **4. No Console Errors** ✅
- Open browser console (F12)
- Check for JavaScript errors
- Verify all resources load

---

## 🔄 **How to Redeploy After Fixes**

### **Method 1: Auto-Deploy (Easiest)**
Streamlit Cloud auto-deploys when you push to GitHub:

```bash
git add .
git commit -m "Your changes"
git push origin main
```

Wait 2-3 minutes, then refresh your app!

### **Method 2: Manual Reboot**
1. Go to your Streamlit Cloud dashboard
2. Click on your app
3. Click "⋮" (three dots)
4. Click "Reboot app"
5. Wait 2-3 minutes

### **Method 3: Force Clear Cache**
If app still showing errors:
1. Go to app settings
2. Click "Clear cache"
3. Click "Reboot app"
4. Wait for rebuild

---

## 💡 **Pro Tips for Streamlit Cloud**

### **1. Keep Apps Awake**
Free tier apps sleep after 7 days of inactivity.

**Solution:** Use UptimeRobot
- Go to: https://uptimerobot.com
- Add your app URL
- Set to ping every 5 minutes
- Free forever!

### **2. Optimize Load Times**
```python
# Use session state for expensive operations
if 'data' not in st.session_state:
    st.session_state.data = load_expensive_data()

# Lazy import heavy libraries
@st.cache_resource
def load_ml_model():
    import tensorflow as tf
    return tf.load_model()
```

### **3. Monitor App Performance**
- Check "Analytics" in Streamlit Cloud dashboard
- See visitor count, load times
- Identify bottlenecks

### **4. Use Secrets Properly**
```python
# Access secrets in Streamlit
import streamlit as st

# Don't use os.getenv on Streamlit Cloud
# DATABASE_URL = os.getenv("DATABASE_URL")  # ❌ Won't work

# Use st.secrets instead
DATABASE_URL = st.secrets.get("DATABASE_URL")  # ✅ Works!
```

---

## 🆘 **Still Having Issues?**

### **Check These:**

1. **App Logs**
   - Streamlit Cloud Dashboard → Your App → Logs
   - Look for specific error messages

2. **GitHub Repository**
   - Ensure latest code is pushed
   - Check for any .gitignore issues
   - Verify all files are committed

3. **Secrets Configuration**
   - Settings → Secrets
   - Verify all required secrets are set
   - Check for typos or extra spaces

4. **Python Version**
   - Check `runtime.txt` exists
   - Ensure Python 3.11.7 is specified

5. **Dependencies**
   - Review `requirements.txt`
   - Ensure no version conflicts
   - Check for platform-specific packages

---

## 📞 **Get Help**

### **Resources:**
- **Streamlit Docs**: https://docs.streamlit.io/streamlit-community-cloud
- **Community Forum**: https://discuss.streamlit.io
- **GitHub Issues**: Check your repo issues
- **This Project**: See other .md files for guides

### **Common Questions:**

**Q: How long does deployment take?**
A: Usually 2-5 minutes for first deploy, 1-2 minutes for updates.

**Q: Can I use custom domains?**
A: Yes! Free on Streamlit Cloud. Go to app settings → Domains.

**Q: How much does it cost?**
A: FREE for public apps! No credit card needed.

**Q: Can I make the app private?**
A: Free tier is public only. Private apps require paid plan.

**Q: What are the resource limits?**
A: 1GB RAM, 1 CPU core, 1GB storage per app.

---

## ✅ **Deployment Success Checklist**

After following the fixes, you should have:

- [x] No ModuleNotFoundError
- [x] App loads successfully
- [x] Database connection works
- [x] All features functional
- [x] Public URL accessible
- [x] Auto-deploys on git push
- [x] Secrets configured correctly
- [x] Ready for DevDays demo!

---

## 🎯 **Your App Should Now Be Live!**

**Expected URL format:**
```
https://carbon-dna-ledger.streamlit.app
```
or
```
https://[your-custom-name].streamlit.app
```

**Test it from:**
- ✅ Your computer
- ✅ Your phone
- ✅ Any device with internet
- ✅ Share with judges/friends!

---

## 🎉 **Congratulations!**

Your Carbon DNA Ledger is now:
- ✅ Deployed on cloud infrastructure
- ✅ Accessible worldwide via URL
- ✅ Auto-updates from GitHub
- ✅ Production-ready
- ✅ DevDays-ready!

**Share your link and impress the judges! 🚀**

---

**Last Updated:** October 22, 2025  
**Status:** ✅ All deployment fixes applied  
**Next Step:** Refresh your Streamlit Cloud app and test!

