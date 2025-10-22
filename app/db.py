"""
Database configuration and session management
"""
# Load environment variables (optional for local dev)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Running on cloud platform or dotenv not available
    pass

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get database URL from environment - FORCE SUPABASE POSTGRESQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Nischita%409@db.mfegdhndowdtphrqazrl.supabase.co:5432/postgres")
if not DATABASE_URL or DATABASE_URL.strip() == "":
    DATABASE_URL = "postgresql://postgres:Nischita%409@db.mfegdhndowdtphrqazrl.supabase.co:5432/postgres"

# ENSURE WE NEVER USE SQLITE - ALWAYS USE SUPABASE POSTGRESQL
if DATABASE_URL.startswith("sqlite"):
    print("[BOOT] WARNING: SQLite detected, forcing Supabase PostgreSQL!")
    DATABASE_URL = "postgresql://postgres:Nischita%409@db.mfegdhndowdtphrqazrl.supabase.co:5432/postgres"

# Normalize Postgres URL and prefer psycopg v3 driver when available
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if DATABASE_URL.startswith("postgresql://") and "+" not in DATABASE_URL:
    # Default to psycopg (v3) if a specific driver is not provided
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Boot log (mask secrets)
try:
    if DATABASE_URL.startswith("sqlite"):
        safe_db = "sqlite:///./carbon_dna.db"
    else:
        safe_db = "postgresql://***@***:5432/postgres"
    print(f"[BOOT] Using DATABASE_URL -> {safe_db}")
except Exception:
    pass

def _create_engine(url: str):
    """Create PostgreSQL engine for Supabase - SQLite not supported"""
    if url.startswith("sqlite"):
        raise Exception("SQLite is not supported. This application requires Supabase PostgreSQL.")
    
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )

# Create SQLAlchemy engine - SUPABASE POSTGRESQL ONLY
print(f"[BOOT] Creating engine for Supabase PostgreSQL: {DATABASE_URL[:50]}...")
engine = _create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Test connection to Supabase PostgreSQL
try:
    with engine.connect() as _conn:
        _conn.exec_driver_sql("SELECT 1")
    print("[BOOT] ✅ Successfully connected to Supabase PostgreSQL")
except Exception as _e:
    print(f"[BOOT] ❌ Failed to connect to Supabase PostgreSQL: {_e}")
    print("[BOOT] This application requires Supabase PostgreSQL - no SQLite fallback!")
    raise Exception("Cannot connect to Supabase PostgreSQL database. Please check your DATABASE_URL.")

# Base class for models
Base = declarative_base()

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
