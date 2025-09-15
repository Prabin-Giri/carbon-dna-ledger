# Carbon DNA Ledger

## Overview

Carbon DNA Ledger is a demo-ready prototype for auditable carbon emission tracking that provides hash-chained integrity verification, complete audit trails, and comprehensive analysis capabilities. The system ingests carbon emission data from CSV files and PDFs, generates "DNA receipts" with complete audit trails from source document to final calculation, and stores data with blockchain-style tamper detection using hash-chained integrity.

Key features include:
- Auditable carbon emission tracking with cryptographic integrity
- DNA receipts showing complete calculation lineage 
- Emission factor matching from curated catalogs
- What-if scenario analysis for parameter testing
- Quality tracking with uncertainty quantification
- Analytics dashboard for trends and insights
- Template-based querying system

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: FastAPI with Uvicorn server providing REST API endpoints
- **Data Layer**: SQLAlchemy ORM with PostgreSQL database for structured data storage
- **Validation**: Pydantic schemas for request/response validation and type safety
- **Service Layer**: Modular services for specialized functionality:
  - `ingest.py`: CSV/PDF parsing and data normalization
  - `hashing.py`: SHA-256 hash chaining for tamper detection
  - `factors.py`: Rule-based emission factor matching
  - `scenario.py`: What-if analysis and parameter modification
  - `analytics.py`: Data aggregation and reporting

### Frontend Architecture
- **UI Framework**: Streamlit serving as the primary user interface
- **Component Structure**: Modular component system with separate files for each major feature:
  - `uploader.py`: File upload and ingestion interface
  - `explorer.py`: Event browsing and filtering
  - `details.py`: Detailed DNA receipt viewing
  - `scenario.py`: What-if scenario analysis interface
  - `analytics.py`: Charts and dashboard analytics
  - `query.py`: Template-based query interface
- **Visualization**: Plotly for interactive charts and data visualization

### Data Integrity System
- **Hash Chaining**: Each carbon event contains a hash of the previous event, creating an immutable chain
- **Cryptographic Hashing**: SHA-256 algorithm for secure fingerprinting
- **DNA Receipts**: Complete audit trail including inputs, emission factors, calculation method, and source documents
- **Tamper Detection**: Any modification to historical data breaks the hash chain, enabling detection

### Data Processing Pipeline
1. **Ingestion**: CSV/PDF parsing with content normalization
2. **Factor Matching**: Rule-based emission factor selection from curated catalog
3. **Calculation**: Emission computation with uncertainty quantification
4. **Storage**: PostgreSQL persistence with hash-chained integrity
5. **Analysis**: Real-time analytics and scenario modeling

### Database Schema
- **Suppliers**: Company information and data quality scores
- **Emission Factors**: Curated catalog of emission calculation factors
- **Carbon Events**: Individual emission events with DNA receipts and hash chains
- **Relational Design**: Foreign key relationships maintaining data integrity

## External Dependencies

### Database
- **Supabase PostgreSQL**: External managed PostgreSQL database for production-grade data persistence
- **Connection**: Uses postgresql+psycopg2 driver with connection pooling
- **Extensions**: UUID generation capabilities for unique identifiers

### Python Libraries
- **fastapi**: Web framework for REST API development
- **uvicorn**: ASGI server for serving FastAPI applications
- **sqlalchemy**: ORM for database operations and schema management
- **psycopg2-binary**: PostgreSQL database adapter
- **pydantic**: Data validation and serialization
- **streamlit**: Web UI framework for dashboard interface
- **pdfplumber**: PDF text extraction for document parsing
- **pandas**: Data manipulation and analysis
- **plotly**: Interactive data visualization and charting
- **python-multipart**: File upload handling

### Deployment Platform
- **Replit**: Cloud development and hosting platform
- **Process Management**: Dual process setup running both FastAPI backend and Streamlit frontend
- **Environment Configuration**: Uses Replit Secrets for secure database connection management

### File Processing
- **CSV Processing**: Built-in Python csv module for structured data parsing
- **PDF Processing**: pdfplumber for text-based PDF content extraction (no OCR)
- **Data Validation**: Pydantic schemas for input validation and type checking

### Security & Configuration
- **Environment Variables**: Database connection strings and configuration via Replit Secrets
- **CORS**: Cross-origin resource sharing enabled for Streamlit-FastAPI communication
- **No Authentication**: Demo-only configuration without user authentication system