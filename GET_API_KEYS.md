# 🔑 Getting Your API Keys - Quick Guide

## Required API Keys for Full Functionality

Your Carbon DNA Ledger needs these API keys to work fully:

---

## 1️⃣ **Supabase PostgreSQL Database URL** (REQUIRED)

### **What It's For:**
- Storing all emission records
- Audit snapshots
- Compliance data

### **How to Get It:**
1. Go to: https://supabase.com
2. Sign in or create account (FREE)
3. Create a new project (or use existing)
4. Go to: **Project Settings** → **Database**
5. Copy the **Connection String** (URI format)

### **Format:**
```
postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres
```

### **Where to Use:**
```toml
DATABASE_URL = "postgresql://postgres:YOUR-PASSWORD@db.PROJECT.supabase.co:5432/postgres"
```

**⚠️ Important:** You already have this from your current setup!

---

## 2️⃣ **OpenAI API Key** (REQUIRED for AI Features)

### **What It's For:**
- AI-powered text classification
- LLM confidence scoring
- Intelligent document processing
- Automated compliance suggestions

### **How to Get It (5 minutes):**

#### **Step 1: Create OpenAI Account**
1. Go to: https://platform.openai.com/signup
2. Sign up with email or Google/Microsoft account
3. Verify your email

#### **Step 2: Add Payment Method**
- Even for free tier, you need to add a card
- You get **$5 FREE credit** to start
- Only charges after you use the free credit
- Can set spending limits to $1-5/month

#### **Step 3: Generate API Key**
1. Go to: https://platform.openai.com/api-keys
2. Click "**+ Create new secret key**"
3. Give it a name (e.g., "Carbon DNA Ledger")
4. Click "**Create secret key**"
5. **COPY THE KEY IMMEDIATELY** (you can't see it again!)

### **Format:**
```
sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### **Where to Use:**
```toml
OPENAI_API_KEY = "sk-proj-your-actual-key-here"
```

### **Free Tier Details:**
- ✅ $5 free credit for new accounts
- ✅ Lasts 1-3 months depending on usage
- ✅ This project uses minimal API calls
- ✅ Can set spending limit to $5/month max
- ✅ Get notifications when credit runs low

### **Cost Estimates for This Project:**
```
Typical Usage:
- Processing 100 records: ~$0.10
- AI classification: ~$0.02 per record
- Monthly cost for 500 records: ~$2-3

Your $5 credit = ~2-3 months of free use!
```

### **Alternative (If You Don't Want to Pay):**
The app will still work without OpenAI API key, but with reduced functionality:
- ❌ No AI classification
- ❌ No LLM confidence scores
- ✅ All other features work (compliance, audits, monitoring)

---

## 🔧 **Quick Setup - All Environment Variables**

### **For Streamlit Cloud:**
```toml
# Copy-paste this into Streamlit Cloud Secrets:

# Database (REQUIRED)
DATABASE_URL = "postgresql://postgres:YOUR-PASSWORD@db.YOUR-PROJECT.supabase.co:5432/postgres"

# Climate TRACE (REQUIRED)
COMPLIANCE_CT_ENABLED = "true"

# Backend URL (REQUIRED for full deployment)
API_BASE = "http://127.0.0.1:8000"

# OpenAI (REQUIRED for AI features)
OPENAI_API_KEY = "sk-proj-your-actual-key-here"
```

### **For Render/Railway:**
```bash
# Add these as environment variables:
DATABASE_URL=postgresql://postgres:YOUR-PASSWORD@db.YOUR-PROJECT.supabase.co:5432/postgres
COMPLIANCE_CT_ENABLED=true
OPENAI_API_KEY=sk-proj-your-actual-key-here
```

---

## 🎯 **For DevDays Demo:**

### **Option 1: Full AI Features (Recommended)**
✅ Get OpenAI API key ($5 free credit)  
✅ Enable all features  
✅ Show complete functionality  
✅ Impress judges with AI capabilities  

**Time:** 10 minutes  
**Cost:** $0 (free credit) or $2-3/month after

### **Option 2: Without AI Features**
✅ Deploy without OpenAI key  
✅ Core features still work  
✅ Save money/time  
❌ Missing AI classification  
❌ Missing LLM confidence  

**Time:** 5 minutes  
**Cost:** $0

---

## 🔒 **Security Best Practices:**

### **DO:**
✅ Use environment variables/secrets  
✅ Add `.env` to `.gitignore`  
✅ Never commit API keys to GitHub  
✅ Set spending limits on OpenAI  
✅ Rotate keys periodically  

### **DON'T:**
❌ Hardcode API keys in code  
❌ Share keys publicly  
❌ Commit `.env` files  
❌ Use production keys for testing  
❌ Leave unlimited spending enabled  

---

## 💡 **Tips for Managing API Costs:**

### **OpenAI Cost Control:**
1. **Set Usage Limits:**
   - Go to: https://platform.openai.com/account/limits
   - Set "Monthly budget" to $5 or $10
   - Set "Email alerts" at 50% and 80%

2. **Monitor Usage:**
   - Check: https://platform.openai.com/usage
   - See daily breakdown
   - Track which features use most credits

3. **Optimize Calls:**
   - App already optimized for minimal API calls
   - Only calls AI when needed
   - Uses caching where possible

### **Expected Usage:**
```
DevDays Demo (1 day):
- Upload 50 test records: ~$0.50
- Demo AI features 10 times: ~$0.20
- Total: ~$0.70 for entire demo day

Regular Use (1 month):
- Process 500 records: ~$2-3
- Monthly monitoring: included
- Total: ~$3-5/month
```

---

## 🆘 **Troubleshooting:**

### **"Invalid API Key" Error**
✅ **Solution:**
- Check key starts with `sk-proj-` or `sk-`
- Ensure no extra spaces
- Copy the full key (usually ~51 characters)
- Generate new key if lost

### **"Rate Limit Exceeded"**
✅ **Solution:**
- You're on free tier with limits
- Wait a few minutes
- Upgrade to paid tier for higher limits
- Or reduce usage frequency

### **"Insufficient Quota"**
✅ **Solution:**
- Free credit exhausted
- Add payment method
- Check usage at platform.openai.com/usage
- Set budget limit

### **"Database Connection Failed"**
✅ **Solution:**
- Check Supabase project is active
- Verify password is URL-encoded
- Ensure database allows public connections
- Test connection string locally first

---

## 📋 **Pre-Deployment Checklist:**

Before deploying, make sure you have:

- [ ] Supabase DATABASE_URL ready
- [ ] OpenAI API KEY obtained (if using AI features)
- [ ] Both keys tested locally
- [ ] Keys added to deployment platform
- [ ] Spending limits set on OpenAI
- [ ] `.env` file in `.gitignore`
- [ ] No keys committed to GitHub

---

## 🚀 **Quick Links:**

- **Supabase Dashboard**: https://app.supabase.com
- **OpenAI API Keys**: https://platform.openai.com/api-keys
- **OpenAI Usage**: https://platform.openai.com/usage
- **OpenAI Billing**: https://platform.openai.com/account/billing

---

## 💰 **Cost Summary:**

### **Free Tier:**
- Supabase: **FREE** (500MB database, 2GB bandwidth)
- OpenAI: **$5 FREE** credit (new accounts)
- Streamlit Cloud: **FREE** (unlimited public apps)
- Render: **FREE** (750 hrs/month)

### **Total Monthly Cost:**
- **$0-3/month** for full functionality
- **$0/month** without AI features
- Perfect for DevDays demo!

---

## ✅ **You're All Set!**

With these API keys configured, your Carbon DNA Ledger will have:
- ✅ Full database functionality
- ✅ AI-powered classification
- ✅ LLM confidence scoring
- ✅ Real-time monitoring
- ✅ Complete compliance tracking
- ✅ Production-ready deployment

**Now go deploy following `DEPLOY_NOW.md`! 🚀**

---

**Last Updated:** October 22, 2025  
**Free Credits Available:** $5 OpenAI (new accounts)  
**Estimated Setup Time:** 10-15 minutes

