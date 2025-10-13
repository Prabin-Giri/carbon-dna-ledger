# Carbon DNA Ledger

A comprehensive carbon emissions tracking, compliance management, and climate intelligence platform with AI-powered insights.

## 🌍 Overview

Carbon DNA Ledger is a full-stack application designed to help organizations track, analyze, and manage their carbon emissions data with advanced compliance features, audit capabilities, and climate intelligence tools.

## ✨ Key Features

### 📊 **Emission Data Management**
- **Multi-format Data Ingestion**: Upload CSV files, process invoices, and integrate with various data sources
- **AI-Powered Classification**: Automatic categorization and validation of emission records
- **Real-time Data Processing**: Instant data validation and quality scoring
- **Tamper Detection**: Cryptographic integrity verification using Merkle trees

### 🏛️ **Compliance Intelligence**
- **Multi-Framework Support**: EPA, EU ETS, TCFD, SEC, CARB, CDP, GRI, SASB, CSRD, and more
- **Regulatory Readiness Assessment**: Automated compliance gap analysis
- **AI-Powered Roadmaps**: Dynamic compliance planning with actionable steps
- **Audit Trail Management**: Comprehensive audit snapshots with immutable history

### 🔍 **Advanced Analytics**
- **Emission Trends & Deltas**: Month-over-month analysis and trend identification
- **Top Emitters Analysis**: Supplier and activity-based emission ranking
- **Quality Gap Detection**: Data quality assessment and improvement recommendations
- **Scenario Modeling**: What-if analysis for operational changes

### 🌱 **Climate Intelligence**
- **Climate TRACE Integration**: Benchmark against global emission datasets
- **Carbon Rewards Engine**: Identify offset opportunities, tax credits, and grants
- **Cost-Benefit Analysis**: Financial impact assessment of climate initiatives
- **Risk Assessment**: Climate risk evaluation and mitigation strategies

### 🔒 **Security & Integrity**
- **Immutable Audit Logs**: Event-sourced architecture for complete data provenance
- **Cryptographic Verification**: Merkle root hashing for data integrity
- **Role-based Access Control**: Secure multi-user environment
- **Data Encryption**: End-to-end data protection

## 🏗️ Architecture

### Backend (FastAPI)
- **RESTful API**: Comprehensive API endpoints for all functionality
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI Integration**: OpenAI GPT for intelligent data processing
- **Background Jobs**: Asynchronous processing for large datasets

### Frontend (Streamlit)
- **Interactive Dashboard**: Real-time data visualization and analysis
- **User-friendly Interface**: Intuitive design for non-technical users
- **Responsive Design**: Works across desktop and mobile devices
- **Real-time Updates**: Live data synchronization

### Key Components
```
app/
├── main.py                 # FastAPI application
├── models.py              # Database models
├── schemas.py             # Pydantic schemas
├── services/              # Business logic
│   ├── compliance_integrity_engine.py
│   ├── enhanced_audit_snapshot.py
│   ├── advanced_compliance_engine.py
│   ├── climate_trace.py
│   ├── rewards_engine.py
│   └── analytics.py
└── api_*.py              # API routers

ui/
├── app.py                # Streamlit main application
└── components/           # UI components
    ├── enhanced_audit_snapshots.py
    ├── enhanced_compliance_roadmap.py
    ├── advanced_compliance_dashboard.py
    ├── climate_trace.py
    └── analytics.py
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL (or SQLite for development)
- OpenAI API key (optional, for AI features)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Prabin-Giri/carbon-dna-ledger.git
   cd carbon-dna-ledger
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   python -m app.db
   ```

6. **Start the application**
   ```bash
   # Start backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # Start frontend (in another terminal)
   streamlit run ui/app.py --server.port 8501
   ```

7. **Access the application**
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 📋 Usage

### 1. Data Upload
- Navigate to the **Data Upload** section
- Upload CSV files with emission data
- Use AI-powered classification for automatic data processing
- Review and validate data quality scores

### 2. Compliance Management
- Access **Compliance Intelligence Dashboard**
- Create audit snapshots for regulatory reporting
- Generate compliance roadmaps with AI assistance
- Track regulatory readiness across multiple frameworks

### 3. Analytics & Insights
- Explore **Analytics Dashboard** for emission trends
- Use **What-If Scenarios** for operational planning
- Identify **Carbon Rewards** opportunities
- Compare data against **Climate TRACE** benchmarks

### 4. Audit & Reporting
- Generate comprehensive audit snapshots
- Export data for regulatory submissions
- Track data provenance and integrity
- Maintain immutable audit trails

## 🔧 Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/carbon_dna

# OpenAI (optional)
OPENAI_API_KEY=your_openai_api_key

# Climate TRACE
CLIMATE_TRACE_API_KEY=your_climate_trace_key

# Security
SECRET_KEY=your_secret_key
```

### Database Setup
The application supports both PostgreSQL (production) and SQLite (development). Configure your database connection in the `.env` file.

## 📊 API Documentation

The API is fully documented with OpenAPI/Swagger. Access the interactive documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key API Endpoints
- `GET /api/emission-records` - Retrieve emission data
- `POST /api/upload` - Upload new data files
- `GET /api/compliance/audit-snapshots` - Get audit snapshots
- `POST /api/compliance/roadmap` - Generate compliance roadmap
- `GET /api/analytics/top_emitters` - Get top emitters analysis
- `POST /api/scan-opportunities` - Scan for carbon opportunities

## 🧪 Testing

Run the test suite:
```bash
pytest tests/
```

Run specific test categories:
```bash
pytest tests/test_compliance.py
pytest tests/test_analytics.py
pytest tests/test_audit.py
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Climate TRACE** for global emission data
- **OpenAI** for AI-powered insights
- **FastAPI** and **Streamlit** communities
- **PostgreSQL** and **SQLAlchemy** teams

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Prabin-Giri/carbon-dna-ledger/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Prabin-Giri/carbon-dna-ledger/discussions)
- **Documentation**: [Wiki](https://github.com/Prabin-Giri/carbon-dna-ledger/wiki)

## 🗺️ Roadmap

- [ ] **Mobile App**: Native mobile application
- [ ] **Blockchain Integration**: Decentralized audit trails
- [ ] **Advanced AI**: GPT-4 integration for enhanced insights
- [ ] **Real-time Monitoring**: IoT sensor integration
- [ ] **Carbon Markets**: Trading platform integration
- [ ] **Multi-tenant**: Enterprise multi-organization support

---

**Built with ❤️ for a sustainable future**