# 🚀 Carbon DNA Ledger - Deployment Guide

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/Prabin-Giri/carbon-dna-ledger.git
cd carbon-dna-ledger
```

### 2. Install Dependencies
```bash
# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all requirements
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the project root:

```env
# Database Configuration (Supabase PostgreSQL)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres

# Climate TRACE Integration
COMPLIANCE_CT_ENABLED=true

# Optional: OpenAI API Key for AI features
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Server Configuration
API_BASE=http://127.0.0.1:8000
```

### 4. Start the Backend (FastAPI)
```bash
# Option 1: Using the startup script
bash start_server.sh

# Option 2: Manual start
export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres"
export COMPLIANCE_CT_ENABLED=true
python3 -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
```

### 5. Start the Frontend (Streamlit)
In a new terminal:

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start Streamlit
streamlit run ui/app.py --server.port 8501
```

### 6. Access the Application
- **Frontend UI**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 📦 System Requirements

### Minimum Requirements
- **Python**: 3.9 or higher
- **RAM**: 4GB minimum (8GB recommended)
- **Storage**: 1GB free space
- **Database**: Supabase PostgreSQL (or any PostgreSQL 13+)

### Required External Dependencies
For document processing features:
- **Tesseract OCR**: Required for pytesseract
  ```bash
  # macOS
  brew install tesseract
  
  # Ubuntu/Debian
  sudo apt-get install tesseract-ocr
  
  # Windows
  # Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
  ```

---

## 🔧 Configuration Options

### Database Setup
The application requires Supabase PostgreSQL. To set up:

1. Create a Supabase project at https://supabase.com
2. Get your database connection string from project settings
3. Add to `.env` file as `DATABASE_URL`

### Climate TRACE Integration
Enable real-time monitoring and compliance checking:
```env
COMPLIANCE_CT_ENABLED=true
```

### API Configuration
Customize server settings:
```env
API_BASE=http://127.0.0.1:8000
API_PORT=8000
STREAMLIT_PORT=8501
```

---

## 🚀 Production Deployment

### Option 1: Docker Deployment (Recommended)
```bash
# Build Docker image
docker build -t carbon-dna-ledger .

# Run with environment variables
docker run -d -p 8000:8000 -p 8501:8501 \
  -e DATABASE_URL="your_database_url" \
  -e COMPLIANCE_CT_ENABLED=true \
  carbon-dna-ledger
```

### Option 2: Cloud Platform Deployment

#### Heroku
```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
```

#### Railway
1. Connect your GitHub repository
2. Add environment variables
3. Deploy automatically on push

#### Render
1. Connect repository
2. Configure build command: `pip install -r requirements.txt`
3. Configure start command: `bash start_server.sh`

---

## 📊 Features Overview

### Core Features
- ✅ **Real-time Emissions Monitoring**: 24/7 automated tracking
- ✅ **Compliance Intelligence**: Multi-framework compliance analysis
- ✅ **Audit Snapshots**: Immutable regulatory-ready reports
- ✅ **Data Integrity Center**: Climate TRACE integration
- ✅ **Analytics Dashboard**: Comprehensive data visualization
- ✅ **ROI Calculator**: Financial impact analysis
- ✅ **Scenario Modeling**: What-if analysis tools

### DevDays Highlights
- 🌟 **Novelty**: Satellite-based emissions validation
- 🔥 **Difficulty**: Industry-level performance (250+ records/sec)
- 🌍 **Impact**: Prevents regulatory violations, saves millions

---

## 🧪 Testing

### Run Tests
```bash
# All tests
pytest

# Specific test files
pytest test_climate_trace.py
pytest test_emissions_calculator.py
pytest test_enhanced_audit.py
```

### API Testing
```bash
# Test backend health
curl http://localhost:8000/health

# Test emission records endpoint
curl http://localhost:8000/api/emission-records?limit=10
```

---

## 📚 Documentation

### API Documentation
- Interactive API docs: http://localhost:8000/docs
- ReDoc format: http://localhost:8000/redoc

### Key Modules
- **Backend**: `app/main.py` - FastAPI application
- **Frontend**: `ui/app.py` - Streamlit dashboard
- **Services**: `app/services/` - Business logic
- **Models**: `app/models.py` - Database schema
- **Components**: `ui/components/` - UI components

---

## 🔐 Security

### Environment Variables
Never commit `.env` files to version control. Use:
```bash
# Add to .gitignore
echo ".env" >> .gitignore
```

### Database Security
- Use strong passwords
- Enable SSL for database connections
- Restrict database access by IP if possible

### API Security
- Use HTTPS in production
- Implement rate limiting
- Add authentication for sensitive endpoints

---

## 🐛 Troubleshooting

### Common Issues

#### "Module not found" errors
```bash
pip install -r requirements.txt --upgrade
```

#### Database connection errors
1. Check `DATABASE_URL` is correct
2. Verify Supabase project is active
3. Check network connectivity

#### Port already in use
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
uvicorn app.main:app --port 8001
```

#### Tesseract not found
```bash
# Install Tesseract OCR (see System Requirements)
# Then verify installation
tesseract --version
```

---

## 📞 Support

### Documentation
- **README.md**: Project overview
- **CLIMATE_TRACE_INTEGRATION.md**: Climate TRACE setup
- **ENHANCED_COMPLIANCE_ROADMAP.md**: Compliance features
- **FACTOR_BREAKDOWN_EXPLANATION.md**: Scoring methodology

### Getting Help
- Check GitHub issues
- Review API documentation at `/docs`
- Contact support for enterprise deployments

---

## 🎯 Quick Demo Setup (DevDays)

For a quick demo presentation:

```bash
# 1. Quick install (2 minutes)
pip install -r requirements.txt

# 2. Set demo environment (30 seconds)
export DATABASE_URL="postgresql://postgres:Nischita%409@db.mfegdhndowdtphrqazrl.supabase.co:5432/postgres"
export COMPLIANCE_CT_ENABLED=true

# 3. Start servers (1 minute)
python3 -m uvicorn app.main:app --reload --port 8000 &
streamlit run ui/app.py --server.port 8501 &

# 4. Wait for startup
sleep 10

# 5. Open browser
open http://localhost:8501
```

### Demo Flow (10 minutes)
1. **Overview** (1 min): Show dashboard and explain problem
2. **Real-time Monitoring** (2 min): Demonstrate live tracking
3. **Compliance Intelligence** (2 min): Create audit snapshot
4. **Data Integrity** (2 min): Factor breakdown analysis
5. **Impact** (2 min): ROI calculator and business value
6. **Q&A** (1 min): Answer questions

---

## 📈 Performance Metrics

### Current Performance
- **Audit Snapshot Creation**: <2 seconds for 500+ records
- **Compliance Calculation**: 250+ records/second
- **Real-time Monitoring**: <100ms latency
- **Database Queries**: Optimized with indexes

### Optimization Tips
- Enable database connection pooling
- Use Redis for caching (optional)
- Enable CDN for static assets in production

---

## 🔄 Updates and Maintenance

### Check for Updates
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

### Database Migrations
```bash
# Run migrations (if any)
alembic upgrade head
```

### Backup Data
```bash
# Backup PostgreSQL database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

---

## 📝 License

This project is part of the Carbon DNA Ledger initiative for DevDays 2025.

---

**Last Updated**: October 22, 2025  
**Version**: 2.0.0  
**GitHub**: https://github.com/Prabin-Giri/carbon-dna-ledger

