"""
Database configuration and session management
"""
from dotenv import load_dotenv
load_dotenv()
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./carbon_dna.db")
if not DATABASE_URL or DATABASE_URL.strip() == "":
    DATABASE_URL = "sqlite:///./carbon_dna.db"

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
    if url.startswith("sqlite"):
        return create_engine(
            url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False,
            connect_args={"check_same_thread": False}
        )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )

# Create SQLAlchemy engine with fallback to SQLite if Postgres auth fails or URL is placeholder
if DATABASE_URL.startswith("sqlite"):
    # Ensure absolute path for SQLite to avoid CWD issues
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_root, "carbon_dna.db")
    # Make sure directory exists and file is creatable
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        if not os.path.exists(db_path):
            with open(db_path, 'a'):
                pass
    except Exception as _e:
        print(f"[BOOT] SQLite path prep failed: {_e}")
    DATABASE_URL = f"sqlite:///{db_path}"
    print(f"[BOOT] SQLite path set to {DATABASE_URL}")

engine = _create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Probe connection early to surface misconfig and optionally fallback
try:
    with engine.connect() as _conn:
        _conn.exec_driver_sql("SELECT 1")
except Exception as _e:
    # For local development, if DB connection fails, fall back to SQLite so the app can start
    print(f"[BOOT] Database connection check failed: {_e}")
    print("[BOOT] Falling back to local SQLite database for development.")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_root, "carbon_dna.db")
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        if not os.path.exists(db_path):
            with open(db_path, 'a'):
                pass
    except Exception as _e2:
        print(f"[BOOT] SQLite path prep failed during fallback: {_e2}")
    DATABASE_URL = f"sqlite:///{db_path}"
    print(f"[BOOT] SQLite path set to {DATABASE_URL}")
    engine = _create_engine(DATABASE_URL)
    SessionLocal.configure(bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
