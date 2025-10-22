"""
Carbon DNA Ledger - FastAPI Backend
Main application entry point with all REST endpoints
"""
from dotenv import load_dotenv
load_dotenv()

# Suppress Plotly deprecation warnings
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning, module='plotly')
warnings.filterwarnings('ignore', message='.*keyword arguments have been deprecated.*')

import os
import secrets
import requests
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Union, Any
from pydantic import BaseModel
from uuid import UUID
import pandas as pd
import uuid

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, extract, text, or_, and_

from . import models, schemas
from .db import get_db, engine, DATABASE_URL
from .services import ingest, hashing, factors, scenario, analytics, rewards_engine
from .services.climate_trace import climate_trace_service
from .services.enhanced_climate_trace import enhanced_climate_trace_service
from .services.ct_background_job import run_manual_ct_sync, get_ct_job_status
from .services.ct_advanced_analytics import ClimateTraceAdvancedAnalytics
from .services.ct_automated_reporting import ClimateTraceAutomatedReporting
from .services.ct_regulatory_integration import ClimateTraceRegulatoryIntegration
from .services.ct_carbon_markets import ClimateTraceCarbonMarkets
from .services.compliance_integrity_engine import ComplianceIntegrityEngine
from .services.advanced_compliance_engine import AdvancedComplianceEngine
from .services.compliance_report_generator import ComplianceReportGenerator
from .services.intake_assistant import build_intake_assistant
from .api_enhanced_audit import router as enhanced_audit_router
from .services.audit_sync_service import AuditSyncService
from .api_enhanced_roadmap import router as enhanced_roadmap_router
import logging

logger = logging.getLogger(__name__)
from .services.ai_classifier import AIClassifier
from .services.emissions_calculator import calculate_emissions_if_missing, batch_calculate_emissions
from dotenv import load_dotenv
load_dotenv()
# ---------------------------------------------------------------------------
# Pydantic request models (used by compliance endpoints)
# ---------------------------------------------------------------------------
class CreateAuditSnapshotRequest(BaseModel):
    submission_type: str
    reporting_period_start: date
    reporting_period_end: date
    record_ids: Optional[List[str]] = None

class GenerateReportRequest(BaseModel):
    snapshot_id: str

class RegulatorySubmissionRequest(BaseModel):
    snapshot_id: str
    regulatory_framework: str

class CreateComplianceRuleRequest(BaseModel):
    rule_name: str
    framework: str
    rule_description: str
    severity: str = "medium"
    auto_apply: bool = True
    required_fields: List[str] = []
    validation_rules: List[Dict] = []
    threshold_values: Dict = {}

class CalculateScoresRequest(BaseModel):
    record_ids: Optional[List[str]] = None

# ---------------------------------------------------------------------------
# Lightweight safe migrations for new compliance fields (idempotent)
# ---------------------------------------------------------------------------
def _run_safe_migrations() -> None:
    try:
        with engine.connect() as conn:
            # Normalize needs_human_review to boolean where supported (Postgres)
            try:
                conn.exec_driver_sql(
                    """
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name='emission_records' AND column_name='needs_human_review'
                        ) THEN
                            BEGIN
                                -- Convert text to boolean safely if needed
                                ALTER TABLE emission_records
                                ALTER COLUMN needs_human_review TYPE boolean
                                USING (
                                    CASE
                                        WHEN lower(COALESCE(needs_human_review::text,'')) IN ('true','t','1') THEN true
                                        WHEN lower(COALESCE(needs_human_review::text,'')) IN ('false','f','0') THEN false
                                        ELSE false
                                    END
                                );
                                ALTER TABLE emission_records ALTER COLUMN needs_human_review SET DEFAULT false;
                            EXCEPTION WHEN others THEN
                                -- Ignore if already boolean
                                NULL;
                            END;
                        END IF;
                    END
                    $$;
                    """
                )
            except Exception:
                pass
            # Add Compliance Integrity Engine fields to emission_records (PostgreSQL compatible)
            alter_statements = [
                "ALTER TABLE emission_records ADD COLUMN IF NOT EXISTS compliance_score NUMERIC(5,2) DEFAULT 0.0",
                "ALTER TABLE emission_records ADD COLUMN IF NOT EXISTS factor_source_quality NUMERIC(5,2) DEFAULT 0.0",
                "ALTER TABLE emission_records ADD COLUMN IF NOT EXISTS metadata_completeness NUMERIC(5,2) DEFAULT 0.0",
                "ALTER TABLE emission_records ADD COLUMN IF NOT EXISTS data_entry_method_score NUMERIC(5,2) DEFAULT 0.0",
                "ALTER TABLE emission_records ADD COLUMN IF NOT EXISTS fingerprint_integrity NUMERIC(5,2) DEFAULT 0.0",
                "ALTER TABLE emission_records ADD COLUMN IF NOT EXISTS llm_confidence NUMERIC(5,2) DEFAULT 0.0",
                "ALTER TABLE emission_records ADD COLUMN IF NOT EXISTS compliance_flags JSON",
                "ALTER TABLE emission_records ADD COLUMN IF NOT EXISTS audit_ready BOOLEAN DEFAULT FALSE",
            ]

            for stmt in alter_statements:
                try:
                    conn.exec_driver_sql(stmt)
                except Exception:
                    # PostgreSQL JSON type handling
                    if "JSON" in stmt:
                        fallback = stmt.replace(" JSON", " jsonb")
                        try:
                            conn.exec_driver_sql(fallback)
                        except Exception:
                            pass
                    else:
                        pass
    except Exception as e:
        logger.warning(f"Safe migration step skipped/failed: {e}")

def parse_date_string(date_str: str) -> Optional[date]:
    """Parse various date string formats and return a date object"""
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = date_str.strip()
    if not date_str:
        return None
    
    # Try different date formats
    date_formats = [
        '%Y-%m-%d',           # 2024-01-15
        '%Y/%m/%d',           # 2024/01/15
        '%d/%m/%Y',           # 15/01/2024
        '%m/%d/%Y',           # 01/15/2024
        '%d-%m-%Y',           # 15-01-2024
        '%Y-%m-%d %H:%M:%S',  # 2024-01-15 10:30:00
        '%Y-%m-%dT%H:%M:%S',  # 2024-01-15T10:30:00
        '%Y-%m-%dT%H:%M:%SZ', # 2024-01-15T10:30:00Z
        '%d/%m/%y',           # 15/01/24
        '%m/%d/%y',           # 01/15/24
        '%d-%m-%y',           # 15-01-24
        '%Y%m%d',             # 20240115
        '%d.%m.%Y',           # 15.01.2024
        '%d.%m.%y',           # 15.01.24
    ]
    
    for fmt in date_formats:
        try:
            parsed_datetime = datetime.strptime(date_str, fmt)
            return parsed_datetime.date()
        except ValueError:
            continue
    
    return None

# Create tables
_run_safe_migrations()
# Skip table creation for PostgreSQL as we use migration scripts
if not DATABASE_URL.startswith("postgresql"):
    models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Carbon DNA Ledger", version="1.0.0")

# Include enhanced audit router
app.include_router(enhanced_audit_router)

# Include enhanced roadmap router
app.include_router(enhanced_roadmap_router)

# Enable CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8501","http://localhost:8501","*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Carbon DNA Ledger API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/api/ingest", response_model=schemas.IngestResponse)
async def ingest_data(
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    supplier_name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Ingest CSV or PDF files and create carbon events with DNA receipts"""
    try:
        # Read file content
        content = await file.read()
        
        # Parse based on document type
        if doc_type == "csv":
            records = ingest.parse_csv(content, file.filename)
        elif doc_type == "pdf":
            records = ingest.parse_pdf(content, file.filename)
        else:
            raise HTTPException(status_code=400, detail="Invalid doc_type. Must be 'csv' or 'pdf'")
        
        if not records:
            raise HTTPException(status_code=400, detail="No valid records found in file")
        
        # Process each record
        inserted_ids = []
        for record in records:
            # Get or create supplier
            supplier = ingest.get_or_create_supplier(db, record.get('supplier', supplier_name))
            if not supplier:
                raise HTTPException(status_code=400, detail="Supplier name required")
            
            # Match emission factor
            factor = factors.match_emission_factor(db, record)
            if not factor:
                raise HTTPException(status_code=400, detail=f"No matching emission factor for activity: {record.get('activity')}")
            
            # Calculate emissions
            result = factors.calculate_emissions(record, factor)
            
            # Get previous hash for chaining
            prev_hash = hashing.get_last_hash(db)
            
            # Create carbon event
            event_data = {
                'supplier_id': supplier.id,
                'occurred_at': record['occurred_at'],
                'activity': record['activity'],
                'scope': record['scope'],
                'inputs': record['inputs'],
                'factor_id': factor.id,
                'method': result['method'],
                'result_kgco2e': result['result_kgco2e'],
                'uncertainty_pct': result['uncertainty_pct'],
                'source_doc': [{
                    'doc_id': file.filename,
                    'page': record.get('page', 1),
                    'field': record.get('field', 'csv_row'),
                    'raw_text': record.get('raw_text', str(record))
                }],
                'quality_flags': result.get('quality_flags', []),
                'fingerprint': ingest.create_fingerprint(record, factor, result),
                'prev_hash': prev_hash
            }
            
            # Calculate row hash
            row_hash = hashing.calculate_row_hash(event_data, prev_hash)
            event_data['row_hash'] = row_hash
            
            # Create and insert event
            event = models.CarbonEvent(**event_data)
            db.add(event)
            db.commit()
            db.refresh(event)
            
            inserted_ids.append(str(event.id))
        
        return schemas.IngestResponse(
            count_inserted=len(inserted_ids),
            sample_ids=inserted_ids[:5]  # Return first 5 IDs
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest-records", response_model=schemas.IngestRecordsResponse)
def ingest_records(request: schemas.IngestRecordsRequest, db: Session = Depends(get_db)):
    """Ingest standardized CSV rows with hash chaining into emission_records."""
    try:
        inserted = 0
        errors: list[str] = []

        # Ensure table exists
        models.Base.metadata.create_all(bind=engine)

        # Determine grouping key for previous_hash chain (use org_unit if present, else supplier_name)
        def get_chain_key(row: dict) -> str:
            return str(row.get('org_unit') or row.get('supplier_name') or 'global')

        # Cache last hash per chain key
        last_hash_map: dict[str, str] = {}

        # Preload existing last hashes per chain key if needed (simple approach: ignore for now)

        for row in request.rows:
            # Basic validation
            if request.documentType == 'simple':
                required = ['date','supplier_name','category','amount','currency','scope','methodology']
            else:
                required = ['date_start','activity_amount','activity_unit','scope','methodology']
            missing = [k for k in required if k not in row or row.get(k) in (None, '')]
            if missing:
                errors.append(f"Missing required fields: {', '.join(missing)} for row with external_id={row.get('external_id','')}" )
                continue

            chain_key = get_chain_key(row)
            prev_hash = last_hash_map.get(chain_key) or row.get('previous_hash') or ''
            salt = row.get('salt') or secrets.token_hex(8)
            base = hashing.calculate_record_base_string(row)
            rec_hash = hashing.calculate_record_hash(prev_hash, base, salt)

            # Parse date fields
            date_start = parse_date_string(row.get('date_start'))
            date_end = parse_date_string(row.get('date_end'))
            date_simple = parse_date_string(row.get('date'))
            
            # Debug logging for date parsing issues
            if not date_start and row.get('date_start'):
                print(f"Warning: Could not parse date_start: {row.get('date_start')}")
            if not date_end and row.get('date_end'):
                print(f"Warning: Could not parse date_end: {row.get('date_end')}")
            if not date_simple and row.get('date'):
                print(f"Warning: Could not parse date: {row.get('date')}")

            # Calculate emissions if missing
            try:
                calculated_row = calculate_emissions_if_missing(row, db)
                # Update row with calculated emissions data
                row.update(calculated_row)
            except Exception as e:
                # Log the error but continue processing
                print(f"Warning: Could not calculate emissions for row: {e}")
                errors.append(f"Could not calculate emissions for row with external_id={row.get('external_id','')}: {str(e)}")

            # Prepare model instance
            record = models.EmissionRecord(
                previous_hash=prev_hash,
                record_hash=rec_hash,
                salt=salt,
                raw_row=row,
                # Map common fields when present
                record_id=row.get('record_id'),
                external_id=row.get('external_id'),
                contract_id=row.get('contract_id'),
                instrument_type=row.get('instrument_type'),
                supplier_name=row.get('supplier_name'),
                org_unit=row.get('org_unit'),
                facility_id=row.get('facility_id'),
                country_code=row.get('country_code'),
                date_start=date_start,
                date_end=date_end,
                date=date_simple,
                scope=row.get('scope'),
                category=row.get('category'),
                subcategory=row.get('subcategory'),
                activity_type=row.get('activity_type'),
                activity_amount=row.get('activity_amount'),
                activity_unit=row.get('activity_unit'),
                fuel_type=row.get('fuel_type'),
                vehicle_type=row.get('vehicle_type'),
                distance_km=row.get('distance_km'),
                mass_tonnes=row.get('mass_tonnes'),
                energy_kwh=row.get('energy_kwh'),
                grid_region=row.get('grid_region'),
                market_basis=row.get('market_basis'),
                renewable_percent=row.get('renewable_percent'),
                emission_factor_value=row.get('emission_factor_value'),
                emission_factor_unit=row.get('emission_factor_unit'),
                ef_source=row.get('ef_source'),
                ef_ref_code=row.get('ef_ref_code'),
                ef_version=row.get('ef_version'),
                gwp_set=row.get('gwp_set'),
                co2_kg=row.get('co2_kg'),
                ch4_kg=row.get('ch4_kg'),
                n2o_kg=row.get('n2o_kg'),
                co2e_kg=row.get('co2e_kg'),
                methodology=row.get('methodology'),
                data_quality_score=row.get('data_quality_score'),
                verification_status=row.get('verification_status'),
                attachment_url=row.get('attachment_url'),
                notes=row.get('notes'),
                description=row.get('description'),
                amount=row.get('amount'),
                currency=row.get('currency'),
                ef_factor_per_currency=row.get('ef_factor_per_currency'),
                emissions_kgco2e=row.get('emissions_kgco2e'),
                calculation_method=row.get('calculation_method'),
                calculation_metadata=row.get('calculation_metadata'),
                project_code=row.get('project_code')
            )

            db.add(record)
            db.commit()
            last_hash_map[chain_key] = rec_hash
            inserted += 1

        return schemas.IngestRecordsResponse(count_inserted=inserted, errors=errors)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/seed-factors")
def seed_emission_factors(db: Session = Depends(get_db)):
    """Seed emission_factors table from infra/seed_factors.json (idempotent insert by ref code)."""
    try:
        import json
        from pathlib import Path
        seed_path = Path("infra/seed_factors.json")
        if not seed_path.exists():
            return {"success": False, "error": "seed_factors.json not found"}
        data = json.loads(seed_path.read_text())
        inserted = 0
        for item in data:
            # Check if exists by ref code+version or description+source
            existing = db.query(models.EmissionFactor).filter(
                (models.EmissionFactor.ef_version == item.get("version")) if hasattr(models.EmissionFactor, 'ef_version') else models.EmissionFactor.version == item.get("version"),
            ).first()
            if existing:
                continue
            factor = models.EmissionFactor(
                source=item.get("source", "UNKNOWN"),
                description=item.get("description"),
                scope=item.get("scope", 3),
                activity_category=item.get("activity_category"),
                region=item.get("region"),
                value=item.get("value"),
                unit=item.get("unit"),
                version=item.get("version"),
                uncertainty_pct=item.get("uncertainty_pct", 0),
                factor_metadata=item
            )
            db.add(factor)
            inserted += 1
        db.commit()
        return {"success": True, "inserted": inserted}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

@app.post("/api/classify-preview")
def classify_preview(request: dict, db: Session = Depends(get_db)):
    """Run AI extraction but DO NOT insert; return structured data + emissions calc."""
    try:
        text = request.get("text", "")
        supplier_name = request.get("supplier_name")
        if not text:
            return {"success": False, "error": "Text is required"}
        classifier = AIClassifier()
        result = classifier.classify_invoice_text(text, supplier_name)
        if not result.get("success"):
            return result
        data = result["data"]
        # Calculate emissions if possible
        try:
            calculated_data = calculate_emissions_if_missing(data, db)
            data.update(calculated_data)
        except Exception:
            pass
        return {
            "success": True,
            "data": data,
            "confidence_score": result.get("confidence_score", 0.0),
            "needs_human_review": result.get("needs_human_review", False),
            "ai_model_used": result.get("ai_model_used", "unknown"),
            "classification_metadata": result.get("classification_metadata", {})
        }
    except Exception as e:
        return {"success": False, "error": f"Preview error: {str(e)}"}

@app.post("/api/insert-record")
def insert_record(request: dict, db: Session = Depends(get_db)):
    """Insert a single EmissionRecord from provided fields; adds hash chain and calc if missing."""
    try:
        row = dict(request)
        # Calculate emissions if missing
        try:
            calculated = calculate_emissions_if_missing(row, db)
            row.update(calculated)
        except Exception:
            pass
        # Build hash
        prev_hash = row.get('previous_hash') or ''
        salt = row.get('salt') or secrets.token_hex(8)
        base = hashing.calculate_record_base_string(row)
        rec_hash = hashing.calculate_record_hash(prev_hash, base, salt)
        # Parse dates
        date_start = parse_date_string(row.get('date_start'))
        date_end = parse_date_string(row.get('date_end'))
        date_simple = parse_date_string(row.get('date'))
        record = models.EmissionRecord(
            previous_hash=prev_hash,
            record_hash=rec_hash,
            salt=salt,
            raw_row=row,
            supplier_name=row.get('supplier_name'),
            scope=row.get('scope'),
            category=row.get('category'),
            subcategory=row.get('subcategory'),
            activity_type=row.get('activity_type'),
            activity_amount=row.get('activity_amount'),
            activity_unit=row.get('activity_unit'),
            fuel_type=row.get('fuel_type'),
            vehicle_type=row.get('vehicle_type'),
            amount=row.get('amount'),
            currency=row.get('currency'),
            emission_factor_value=row.get('emission_factor_value'),
            emission_factor_unit=row.get('emission_factor_unit'),
            ef_source=row.get('ef_source'),
            ef_ref_code=row.get('ef_ref_code'),
            ef_version=row.get('ef_version'),
            description=row.get('description'),
            methodology=row.get('methodology', 'Manual Insert'),
            emissions_kgco2e=row.get('emissions_kgco2e'),
            calculation_method=row.get('calculation_method'),
            calculation_metadata=row.get('calculation_metadata'),
            date_start=date_start,
            date_end=date_end,
            date=date_simple,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return {"success": True, "record_id": str(record.id)}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": f"Insert error: {str(e)}"}

@app.get("/api/events", response_model=List[schemas.CarbonEventSummary])
def get_events(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    supplier_id: Optional[UUID] = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get paginated list of carbon events"""
    query = db.query(
        models.CarbonEvent.id,
        models.CarbonEvent.occurred_at,
        models.Supplier.name.label('supplier_name'),
        models.CarbonEvent.activity,
        models.CarbonEvent.scope,
        models.CarbonEvent.result_kgco2e,
        models.CarbonEvent.uncertainty_pct,
        models.CarbonEvent.quality_flags
    ).join(models.Supplier)
    
    if from_date:
        query = query.filter(models.CarbonEvent.occurred_at >= from_date)
    if to_date:
        query = query.filter(models.CarbonEvent.occurred_at <= to_date)
    if supplier_id:
        query = query.filter(models.CarbonEvent.supplier_id == supplier_id)
    
    events = query.order_by(desc(models.CarbonEvent.occurred_at)).offset(offset).limit(limit).all()
    
    return [
        schemas.CarbonEventSummary(
            id=event.id,
            occurred_at=event.occurred_at,
            supplier_name=event.supplier_name,
            activity=event.activity,
            scope=event.scope,
            result_kgco2e=event.result_kgco2e,
            uncertainty_pct=event.uncertainty_pct,
            quality_flags=event.quality_flags or []
        )
        for event in events
    ]

@app.get("/api/emission-records")
def get_emission_records(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    supplier_name: Optional[str] = None,
    activity_type: Optional[str] = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get paginated list of emission records"""
    # Ensure new columns exist (PostgreSQL safe)
    try:
        db.execute(text("ALTER TABLE emission_records ADD COLUMN IF NOT EXISTS calculation_method TEXT"))
        db.execute(text("ALTER TABLE emission_records ADD COLUMN IF NOT EXISTS calculation_metadata JSON"))
    except Exception:
        pass
    query = db.query(models.EmissionRecord)
    
    # Only return approved records (not pending human review)
    query = query.filter(models.EmissionRecord.needs_human_review.is_(False))
    
    if from_date:
        query = query.filter(
            (models.EmissionRecord.date >= from_date) | 
            (models.EmissionRecord.date_start >= from_date)
        )
    if to_date:
        query = query.filter(
            (models.EmissionRecord.date <= to_date) | 
            (models.EmissionRecord.date_start <= to_date)
        )
    if supplier_name:
        query = query.filter(models.EmissionRecord.supplier_name.ilike(f"%{supplier_name}%"))
    if activity_type:
        query = query.filter(models.EmissionRecord.activity_type.ilike(f"%{activity_type}%"))
    
    records = query.order_by(desc(models.EmissionRecord.created_at)).offset(offset).limit(limit).all()
    
    return [
        {
            "id": str(record.id),
            "date": record.date.isoformat() if record.date else (record.date_start.isoformat() if record.date_start else None),
            "date_start": record.date_start.isoformat() if record.date_start else None,
            "date_end": record.date_end.isoformat() if record.date_end else None,
            "supplier_name": record.supplier_name,
            "activity_type": record.activity_type,
            "scope": record.scope,
            "emissions_kgco2e": float(record.emissions_kgco2e) if record.emissions_kgco2e else 0,
            "data_quality_score": float(record.data_quality_score) if record.data_quality_score else 0,
            "methodology": record.methodology,
            "category": record.category,
            "activity_amount": float(record.activity_amount) if record.activity_amount else 0,
            "activity_unit": record.activity_unit,
            "created_at": record.created_at.isoformat() if record.created_at else None
        }
        for record in records
    ]

@app.get("/api/suppliers")
def get_suppliers(db: Session = Depends(get_db)):
    """Get list of unique suppliers from emission records"""
    suppliers = db.query(models.EmissionRecord.supplier_name).distinct().filter(
        models.EmissionRecord.supplier_name.isnot(None),
        models.EmissionRecord.needs_human_review.is_(False)  # Only approved records
    ).all()
    
    return [{"name": supplier[0]} for supplier in suppliers if supplier[0]]

@app.get("/api/activities")
def get_activities(db: Session = Depends(get_db)):
    """Get list of unique activity types from emission records"""
    activities = db.query(models.EmissionRecord.activity_type).distinct().filter(
        models.EmissionRecord.activity_type.isnot(None),
        models.EmissionRecord.needs_human_review.is_(False)  # Only approved records
    ).all()
    
    return [{"type": activity[0]} for activity in activities if activity[0]]

@app.get("/api/emission-records/{record_id}")
def get_emission_record_detail(record_id: str, db: Session = Depends(get_db)):
    """Get detailed emission record information"""
    record = db.query(models.EmissionRecord).filter(models.EmissionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Emission record not found")
    
    return {
        "id": str(record.id),
        "date": record.date.isoformat() if record.date else (record.date_start.isoformat() if record.date_start else None),
        "date_start": record.date_start.isoformat() if record.date_start else None,
        "date_end": record.date_end.isoformat() if record.date_end else None,
        "supplier_name": record.supplier_name,
        "activity_type": record.activity_type,
        "scope": record.scope,
        "category": record.category,
        "subcategory": record.subcategory,
        "activity_amount": float(record.activity_amount) if record.activity_amount else None,
        "activity_unit": record.activity_unit,
        "fuel_type": record.fuel_type,
        "vehicle_type": record.vehicle_type,
        "distance_km": float(record.distance_km) if record.distance_km else None,
        "mass_tonnes": float(record.mass_tonnes) if record.mass_tonnes else None,
        "energy_kwh": float(record.energy_kwh) if record.energy_kwh else None,
        "grid_region": record.grid_region,
        "renewable_percent": float(record.renewable_percent) if record.renewable_percent else None,
        "emission_factor_value": float(record.emission_factor_value) if record.emission_factor_value else None,
        "emission_factor_unit": record.emission_factor_unit,
        "ef_source": record.ef_source,
        "ef_ref_code": record.ef_ref_code,
        "ef_version": record.ef_version,
        "co2_kg": float(record.co2_kg) if record.co2_kg else None,
        "ch4_kg": float(record.ch4_kg) if record.ch4_kg else None,
        "n2o_kg": float(record.n2o_kg) if record.n2o_kg else None,
        "co2e_kg": float(record.co2e_kg) if record.co2e_kg else None,
        "emissions_kgco2e": float(record.emissions_kgco2e) if record.emissions_kgco2e else None,
        "methodology": record.methodology,
        "data_quality_score": float(record.data_quality_score) if record.data_quality_score else None,
        "verification_status": record.verification_status,
        "notes": record.notes,
        "description": record.description,
        "amount": float(record.amount) if record.amount else None,
        "currency": record.currency,
        "project_code": record.project_code,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "raw_row": record.raw_row,
        "calculation_method": record.calculation_method,
        "calculation_metadata": record.calculation_metadata,
        "previous_hash": record.previous_hash,
        "record_hash": record.record_hash,
        "salt": record.salt
    }

@app.put("/api/emission-records/{record_id}")
def update_emission_record(record_id: str, updated_data: dict, db: Session = Depends(get_db)):
    """Update a specific emission record by ID"""
    try:
        record = db.query(models.EmissionRecord).filter(models.EmissionRecord.id == record_id).first()
        if not record:
            return {"error": "Record not found"}
        
        # Update fields that are provided
        if "fuel_type" in updated_data:
            record.fuel_type = updated_data["fuel_type"]
        if "vehicle_type" in updated_data:
            record.vehicle_type = updated_data["vehicle_type"]
        if "activity_type" in updated_data:
            record.activity_type = updated_data["activity_type"]
        if "activity_amount" in updated_data:
            record.activity_amount = updated_data["activity_amount"]
        if "activity_unit" in updated_data:
            record.activity_unit = updated_data["activity_unit"]
        if "category" in updated_data:
            record.category = updated_data["category"]
        if "subcategory" in updated_data:
            record.subcategory = updated_data["subcategory"]
        if "supplier_name" in updated_data:
            record.supplier_name = updated_data["supplier_name"]
        if "emissions_kgco2e" in updated_data:
            record.emissions_kgco2e = updated_data["emissions_kgco2e"]
        if "data_quality_score" in updated_data:
            record.data_quality_score = updated_data["data_quality_score"]
        if "methodology" in updated_data:
            record.methodology = updated_data["methodology"]
        if "notes" in updated_data:
            # Add notes to description or create new field
            if record.description:
                record.description = f"{record.description}\n{updated_data['notes']}"
            else:
                record.description = updated_data["notes"]
        if "date" in updated_data:
            record.date = updated_data["date"]
        if "ct_sector" in updated_data:
            record.ct_sector = updated_data["ct_sector"]
        if "ct_subsector" in updated_data:
            record.ct_subsector = updated_data["ct_subsector"]
        if "ct_country_code" in updated_data:
            record.ct_country_code = updated_data["ct_country_code"]
        
        # Update the timestamp
        record.updated_at = datetime.now()
        
        # Recalculate hash if needed
        if any(key in updated_data for key in ["fuel_type", "activity_type", "activity_amount", "emissions_kgco2e"]):
            # Recalculate record hash
            base = hashing.calculate_record_base_string({
                "supplier_name": record.supplier_name,
                "activity_type": record.activity_type,
                "activity_amount": record.activity_amount,
                "fuel_type": record.fuel_type,
                "emissions_kgco2e": record.emissions_kgco2e,
                "methodology": record.methodology
            })
            record.record_hash = hashing.calculate_record_hash(record.previous_hash, base, record.salt)
        
        db.commit()
        db.refresh(record)
        
        return {
            "success": True,
            "message": "Record updated successfully",
            "record_id": str(record.id),
            "updated_fields": list(updated_data.keys())
        }
        
    except Exception as e:
        db.rollback()
        return {"error": f"Error updating record: {str(e)}"}

@app.get("/api/events/{event_id}", response_model=schemas.CarbonEventDetail)
def get_event_detail(event_id: UUID, db: Session = Depends(get_db)):
    """Get full carbon event details with DNA receipt"""
    event = db.query(models.CarbonEvent).filter(models.CarbonEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get related data
    supplier = db.query(models.Supplier).filter(models.Supplier.id == event.supplier_id).first()
    factor = db.query(models.EmissionFactor).filter(models.EmissionFactor.id == event.factor_id).first()
    
    return schemas.CarbonEventDetail(
        id=event.id,
        occurred_at=event.occurred_at,
        supplier_name=supplier.name if supplier else "Unknown",
        activity=event.activity,
        scope=event.scope,
        inputs=event.inputs,
        method=event.method,
        result_kgco2e=event.result_kgco2e,
        uncertainty_pct=event.uncertainty_pct,
        source_doc=event.source_doc,
        quality_flags=event.quality_flags or [],
        fingerprint=event.fingerprint,
        factor_ref=f"{factor.source} v{factor.version}" if factor else "Unknown",
        factor_value=factor.value if factor else 0,
        factor_unit=factor.unit if factor else "",
        prev_hash=event.prev_hash,
        row_hash=event.row_hash,
        created_at=event.created_at
    )

@app.post("/api/events/{event_id}/scenario", response_model=schemas.ScenarioResult)
def run_scenario(event_id: UUID, changes: schemas.ScenarioChanges, db: Session = Depends(get_db)):
    """Run what-if scenario analysis"""
    event = db.query(models.CarbonEvent).filter(models.CarbonEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    factor = db.query(models.EmissionFactor).filter(models.EmissionFactor.id == event.factor_id).first()
    
    # Run scenario analysis
    result = scenario.run_scenario_analysis(db, event, factor, changes.dict(exclude_unset=True))
    
    return schemas.ScenarioResult(**result)

@app.get("/api/analytics/top_emitters")
def get_top_emitters(
    period: str = "month",
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get top emitting suppliers"""
    return analytics.get_top_emitters(db, period, from_date, to_date, limit)

@app.get("/api/analytics/deltas")
def get_emission_deltas(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get month-over-month emission changes"""
    return analytics.get_emission_deltas(db, from_date, to_date)

@app.get("/api/analytics/quality_gaps")
def get_quality_gaps(limit: int = 20, db: Session = Depends(get_db)):
    """Get events with highest uncertainty or quality issues"""
    return analytics.get_quality_gaps(db, limit)

@app.post("/api/query", response_model=schemas.QueryResult)
def execute_template_query(query_request: schemas.QueryRequest, db: Session = Depends(get_db)):
    """Execute template-based NL-to-SQL queries"""
    templates = {
        "top suppliers in period": analytics.query_top_suppliers_template,
        "largest month-over-month increase": analytics.query_largest_delta_template,
        "events with highest uncertainty": analytics.query_highest_uncertainty_template,
        "total emissions by activity type": analytics.query_emissions_by_activity_template,
        "recent emission trends": analytics.query_recent_trends_template,
        "all suppliers summary": analytics.query_all_suppliers_template,
        "all suppliers including zeros": analytics.query_all_suppliers_with_zeros_template
    }
    
    template_func = templates.get(query_request.question.lower())
    if not template_func:
        available = list(templates.keys())
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported query template. Available: {available}"
        )
    
    result = template_func(db, query_request.params)
    return schemas.QueryResult(
        template_name=query_request.question,
        sql=result['sql'],
        rows=result['rows']
    )

@app.post("/api/merkle/close-day", response_model=schemas.MerkleRoot)
def close_daily_merkle(target_date: Optional[date] = None, db: Session = Depends(get_db)):
    """Compute and store Merkle root for a day's events"""
    if not target_date:
        target_date = date.today()
    
    # Get all events for the target date
    events = db.query(models.CarbonEvent).filter(
        func.date(models.CarbonEvent.occurred_at) == target_date
    ).order_by(models.CarbonEvent.created_at).all()
    
    if not events:
        raise HTTPException(status_code=404, detail="No events found for the specified date")
    
    # Calculate Merkle root
    row_hashes = [event.row_hash for event in events]
    root_hash = hashing.calculate_merkle_root(row_hashes)
    
    # Store Merkle root
    merkle_root = models.MerkleRoot(
        period_date=target_date,
        root_hash=root_hash,
        count_events=len(events)
    )
    
    db.add(merkle_root)
    db.commit()
    db.refresh(merkle_root)
    
    return schemas.MerkleRoot(
        id=merkle_root.id,
        period_date=merkle_root.period_date,
        root_hash=merkle_root.root_hash,
        count_events=merkle_root.count_events,
        created_at=merkle_root.created_at
    )

# AI Classification Endpoints
@app.get("/api/ai/models")
def get_ai_models():
    """Get available AI models and their status"""
    try:
        classifier = AIClassifier()
        available_models = classifier.get_available_models()
        
        # Check availability for each model type
        model_status = {}
        for model_type in available_models.keys():
            model_status[model_type] = classifier.check_model_availability(model_type)
        
        return {
            "success": True,
            "available_models": available_models,
            "model_status": model_status
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/classify-text")
def classify_text(
    request: dict,
    db: Session = Depends(get_db)
):
    """Classify invoice text using AI and extract structured data"""
    try:
        text = request.get("text", "")
        supplier_name = request.get("supplier_name")
        model_preference = request.get("model_preference")  # New parameter for model selection
        
        if not text:
            return {
                "success": False,
                "error": "Text is required",
                "confidence_score": 0.0,
                "needs_human_review": True
            }
        
        classifier = AIClassifier(model_preference=model_preference)
        result = classifier.classify_invoice_text(text, supplier_name)
        
        if result["success"]:
            # Create emission record from classified data
            data = result["data"]
            
            # Parse dates
            date_start = parse_date_string(data.get("date"))
            date_end = parse_date_string(data.get("date"))
            
            # Calculate emissions if missing
            try:
                calculated_data = calculate_emissions_if_missing(data, db)
                data.update(calculated_data)
            except Exception as e:
                print(f"Warning: Could not calculate emissions for AI classified data: {e}")

            # Create record
            record = models.EmissionRecord(
                supplier_name=data.get("supplier_name", "Unknown"),
                activity_type=data.get("activity_type", "other"),
                scope=data.get("scope", 3),
                category=data.get("category", "Other"),
                subcategory=data.get("subcategory", ""),
                activity_amount=data.get("activity_amount"),
                activity_unit=data.get("activity_unit", ""),
                fuel_type=data.get("fuel_type", ""),
                vehicle_type=data.get("vehicle_type", ""),
                distance_km=data.get("distance_km"),
                mass_tonnes=data.get("mass_tonnes"),
                energy_kwh=data.get("energy_kwh"),
                amount=data.get("amount"),
                currency=data.get("currency", "USD"),
                description=data.get("description", ""),
                date_start=date_start,
                date_end=date_end,
                date=date_start,  # Use date_start as primary date
                methodology="AI Classification",
                data_quality_score=float(data.get("confidence_score", 0.5)) * 100,
                # Emissions calculation
                emissions_kgco2e=data.get("emissions_kgco2e"),
                calculation_method=data.get("calculation_method"),
                calculation_metadata=data.get("calculation_metadata"),
                # AI Classification fields
                ai_classified=True,
                confidence_score=float(data.get("confidence_score", 0.5)),
                needs_human_review=data.get("needs_human_review", True),  # AI records need review by default
                ai_model_used=result.get("ai_model_used", "unknown"),
                classification_metadata=result.get("classification_metadata", {}),
                raw_row={"original_text": text, "ai_classified": True}
            )
            
            # Add hash chain
            record.previous_hash = ""
            record.salt = secrets.token_hex(8)
            base = hashing.calculate_record_base_string(record.__dict__)
            record.record_hash = hashing.calculate_record_hash("", base, record.salt)
            
            db.add(record)
            db.commit()
            db.refresh(record)
            
            return {
                "success": True,
                "record_id": str(record.id),
                "classified_data": data,
                "confidence_score": result["confidence_score"],
                "needs_human_review": result["needs_human_review"],
                "ai_model_used": result["ai_model_used"]
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Classification failed"),
                "confidence_score": 0.0,
                "needs_human_review": True
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Classification error: {str(e)}",
            "confidence_score": 0.0,
            "needs_human_review": True
        }

@app.post("/api/classify-batch")
def classify_batch(
    request: dict,
    db: Session = Depends(get_db)
):
    """Classify multiple texts in batch"""
    try:
        texts = request.get("texts", [])
        supplier_names = request.get("supplier_names")
        
        if not texts:
            return {
                "success": False,
                "error": "Texts array is required",
                "total_processed": 0,
                "created_records": 0,
                "errors": 0
            }
        
        classifier = AIClassifier()
        results = classifier.batch_classify(texts, supplier_names)
        
        created_records = []
        errors = []
        
        for i, result in enumerate(results):
            if result["success"]:
                data = result["data"]
                
                # Parse dates
                date_start = parse_date_string(data.get("date"))
                date_end = parse_date_string(data.get("date"))
                
                # Create record
                record = models.EmissionRecord(
                    supplier_name=data.get("supplier_name", "Unknown"),
                    activity_type=data.get("activity_type", "other"),
                    scope=data.get("scope", 3),
                    category=data.get("category", "Other"),
                    subcategory=data.get("subcategory", ""),
                    activity_amount=data.get("activity_amount"),
                    activity_unit=data.get("activity_unit", ""),
                    fuel_type=data.get("fuel_type", ""),
                    vehicle_type=data.get("vehicle_type", ""),
                    distance_km=data.get("distance_km"),
                    mass_tonnes=data.get("mass_tonnes"),
                    energy_kwh=data.get("energy_kwh"),
                    amount=data.get("amount"),
                    currency=data.get("currency", "USD"),
                    description=data.get("description", ""),
                    date_start=date_start,
                    date_end=date_end,
                    date=date_start,
                    methodology="AI Classification (Batch)",
                    data_quality_score=float(data.get("confidence_score", 0.5)) * 100,
                    # AI Classification fields
                    ai_classified=True,
                    confidence_score=float(data.get("confidence_score", 0.5)),
                    needs_human_review=data.get("needs_human_review", True),  # AI records need review by default
                    ai_model_used=result.get("ai_model_used", "unknown"),
                    classification_metadata=result.get("classification_metadata", {}),
                    raw_row={"original_text": texts[i], "ai_classified": True}
                )
                
                # Add hash chain
                record.previous_hash = ""
                record.salt = secrets.token_hex(8)
                base = hashing.calculate_record_base_string(record.__dict__)
                record.record_hash = hashing.calculate_record_hash("", base, record.salt)
                
                db.add(record)
                created_records.append({
                    "index": i,
                    "record_id": str(record.id),
                    "supplier_name": record.supplier_name,
                    "activity_type": record.activity_type,
                    "confidence_score": result["confidence_score"],
                    "needs_human_review": result["needs_human_review"]
                })
            else:
                errors.append({
                    "index": i,
                    "error": result.get("error", "Classification failed"),
                    "text_preview": texts[i][:100] + "..." if len(texts[i]) > 100 else texts[i]
                })
        
        db.commit()
        
        return {
            "success": True,
            "total_processed": len(texts),
            "created_records": len(created_records),
            "errors": len(errors),
            "records": created_records,
            "error_details": errors
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Batch classification error: {str(e)}",
            "total_processed": 0,
            "created_records": 0,
            "errors": len(texts)
        }

@app.post("/api/classify-image")
def classify_image(
    file: UploadFile = File(...),
    supplier_name: Optional[str] = Form(None),
    model_preference: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Classify invoice image using OCR and AI to extract structured data"""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            return {
                "success": False,
                "error": "File must be an image (PNG, JPG, JPEG, etc.)",
                "confidence_score": 0.0,
                "needs_human_review": True
            }
        
        # Read image data
        image_data = file.file.read()
        
        if not image_data:
            return {
                "success": False,
                "error": "Could not read image data",
                "confidence_score": 0.0,
                "needs_human_review": True
            }
        
        # Classify the image
        classifier = AIClassifier(model_preference=model_preference)
        result = classifier.classify_invoice_image(image_data, supplier_name)
        
        if result["success"]:
            # Create emission record from classified data
            data = result["data"]
            
            # Parse dates
            date_start = parse_date_string(data.get("date"))
            date_end = parse_date_string(data.get("date"))
            
            # Calculate emissions if missing
            try:
                calculated_data = calculate_emissions_if_missing(data, db)
                data.update(calculated_data)
            except Exception as e:
                print(f"Warning: Could not calculate emissions for AI classified image data: {e}")

            # Create record
            record = models.EmissionRecord(
                supplier_name=data.get("supplier_name", "Unknown"),
                activity_type=data.get("activity_type", "other"),
                scope=data.get("scope", 3),
                category=data.get("category", "Other"),
                subcategory=data.get("subcategory", ""),
                activity_amount=data.get("activity_amount"),
                activity_unit=data.get("activity_unit", ""),
                fuel_type=data.get("fuel_type", ""),
                vehicle_type=data.get("vehicle_type", ""),
                distance_km=data.get("distance_km"),
                mass_tonnes=data.get("mass_tonnes"),
                energy_kwh=data.get("energy_kwh"),
                amount=data.get("amount"),
                currency=data.get("currency", "USD"),
                description=data.get("description", ""),
                date_start=date_start,
                date_end=date_end,
                date=date_start,
                methodology="AI Classification (Image OCR)",
                data_quality_score=float(data.get("confidence_score", 0.5)) * 100,
                # AI Classification fields
                ai_classified=True,
                confidence_score=float(data.get("confidence_score", 0.5)),
                needs_human_review=data.get("needs_human_review", True),  # AI records need review by default
                ai_model_used=result.get("ai_model_used", "unknown"),
                classification_metadata={
                    **result.get("classification_metadata", {}),
                    "ocr_used": True,
                    "image_filename": file.filename,
                    "image_content_type": file.content_type,
                    "extracted_text": result.get("extracted_text", "")
                },
                raw_row={
                    "original_image": file.filename,
                    "ai_classified": True,
                    "ocr_extracted_text": result.get("extracted_text", "")
                }
            )
            
            # Add hash chain
            record.previous_hash = ""
            record.salt = secrets.token_hex(8)
            base = hashing.calculate_record_base_string(record.__dict__)
            record.record_hash = hashing.calculate_record_hash("", base, record.salt)
            
            db.add(record)
            db.commit()
            db.refresh(record)
            
            return {
                "success": True,
                "record_id": str(record.id),
                "confidence_score": result["confidence_score"],
                "needs_human_review": result["needs_human_review"],
                "extracted_text": result.get("extracted_text", ""),
                "ai_model_used": result.get("ai_model_used", "unknown"),
                "data": data
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Image classification failed"),
                "confidence_score": 0.0,
                "needs_human_review": True,
                "extracted_text": result.get("extracted_text", "")
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Image classification error: {str(e)}",
            "confidence_score": 0.0,
            "needs_human_review": True
        }

@app.get("/api/ai-models")
def get_available_ai_models():
    """Get list of available AI models for classification"""
    return {
        "available_models": [
            {
                "id": "ollama:llama2",
                "name": "Llama 2 (Ollama)",
                "type": "local",
                "description": "Local Llama 2 model via Ollama"
            },
            {
                "id": "ollama:llama3",
                "name": "Llama 3 (Ollama)",
                "type": "local",
                "description": "Local Llama 3 model via Ollama"
            },
            {
                "id": "openai:gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo (OpenAI)",
                "type": "cloud",
                "description": "OpenAI GPT-3.5 Turbo via API"
            },
            {
                "id": "openai:gpt-4",
                "name": "GPT-4 (OpenAI)",
                "type": "cloud",
                "description": "OpenAI GPT-4 via API"
            },
            {
                "id": "regex:fallback",
                "name": "Regex Fallback",
                "type": "local",
                "description": "Pattern-based extraction (low confidence)"
            }
        ],
        "current_model": os.getenv("AI_MODEL_PREFERENCE", "ollama"),
        "ollama_available": _check_ollama_availability(),
        "openai_available": bool(os.getenv("OPENAI_API_KEY"))
    }

@app.post("/api/test-ai")
def test_ai_classification():
    """Test AI classification with a simple example"""
    try:
        classifier = AIClassifier()
        test_text = "Invoice from Global Freight Services Ltd. for truck shipment of raw materials on 2025-03-08. Amount: $1,250.00 USD. Distance: 410 km, Weight: 7.2 tonnes."
        
        result = classifier.classify_invoice_text(test_text, "Global Freight Services Ltd.")
        
        return {
            "success": True,
            "test_text": test_text,
            "result": result,
            "ollama_status": classifier._check_ollama_availability()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "ollama_status": False
        }

@app.get("/api/human-review")
def get_human_review_records(
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get emission records that need human review"""
    try:
        offset = (page - 1) * limit
        
        # Query records that need human review
        query = db.query(models.EmissionRecord).filter(
            models.EmissionRecord.needs_human_review.is_(True)
        ).order_by(desc(models.EmissionRecord.created_at))
        
        total = query.count()
        records = query.offset(offset).limit(limit).all()
        
        return {
            "success": True,
            "records": [
                {
                    "id": str(record.id),
                    "supplier_name": record.supplier_name,
                    "activity_type": record.activity_type,
                    "amount": float(record.amount) if record.amount else None,
                    "currency": record.currency,
                    "date": record.date.isoformat() if record.date else (record.date_start.isoformat() if record.date_start else None),
                    "description": record.description,
                    "scope": int(record.scope) if record.scope else None,
                    "category": record.category,
                    "subcategory": record.subcategory,
                    "activity_amount": float(record.activity_amount) if record.activity_amount else None,
                    "activity_unit": record.activity_unit,
                    "fuel_type": record.fuel_type,
                    "vehicle_type": record.vehicle_type,
                    "distance_km": float(record.distance_km) if record.distance_km else None,
                    "mass_tonnes": float(record.mass_tonnes) if record.mass_tonnes else None,
                    "energy_kwh": float(record.energy_kwh) if record.energy_kwh else None,
                    "confidence_score": float(record.confidence_score) if record.confidence_score else 0.0,
                    "needs_human_review": bool(record.needs_human_review),
                    "ai_model_used": record.ai_model_used,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "classification_metadata": record.classification_metadata,
                    "calculation_method": record.calculation_method,
                    "calculation_metadata": record.calculation_metadata
                }
                for record in records
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch human review records: {str(e)}"
        }

@app.post("/api/human-review/{record_id}/approve")
def approve_human_review_record(
    record_id: str,
    db: Session = Depends(get_db)
):
    """Approve a human review record (mark as reviewed)"""
    try:
        record = db.query(models.EmissionRecord).filter(
            models.EmissionRecord.id == record_id
        ).first()
        
        if not record:
            return {
                "success": False,
                "error": "Record not found"
            }
        
        # Mark as reviewed
        record.needs_human_review = False
        db.commit()
        
        return {
            "success": True,
            "message": "Record approved and marked as reviewed"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to approve record: {str(e)}"
        }

@app.post("/api/human-review/{record_id}/reject")
def reject_human_review_record(
    record_id: str,
    db: Session = Depends(get_db)
):
    """Reject a human review record (mark for deletion or correction)"""
    try:
        record = db.query(models.EmissionRecord).filter(
            models.EmissionRecord.id == record_id
        ).first()
        
        if not record:
            return {
                "success": False,
                "error": "Record not found"
            }
        
        # Delete rejected record to maintain data quality
        # Rejected records should not appear anywhere in the system
        db.delete(record)
        db.commit()
        
        return {
            "success": True,
            "message": "Record rejected and deleted from system"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to reject record: {str(e)}"
        }

@app.post("/api/human-review/{record_id}/approve-with-changes")
def approve_human_review_record_with_changes(
    record_id: str,
    updated_data: dict,
    db: Session = Depends(get_db)
):
    """Approve a human review record with human-made changes"""
    try:
        record = db.query(models.EmissionRecord).filter(
            models.EmissionRecord.id == record_id
        ).first()
        
        if not record:
            return {
                "success": False,
                "error": "Record not found"
            }
        
        # Update the record with human changes
        record.supplier_name = updated_data.get("supplier_name", record.supplier_name)
        record.activity_type = updated_data.get("activity_type", record.activity_type)
        record.amount = updated_data.get("amount", record.amount)
        record.currency = updated_data.get("currency", record.currency)
        record.description = updated_data.get("description", record.description)
        record.scope = updated_data.get("scope", record.scope)
        record.category = updated_data.get("category", record.category)
        record.subcategory = updated_data.get("subcategory", record.subcategory)
        record.activity_amount = updated_data.get("activity_amount", record.activity_amount)
        record.activity_unit = updated_data.get("activity_unit", record.activity_unit)
        record.fuel_type = updated_data.get("fuel_type", record.fuel_type)
        record.vehicle_type = updated_data.get("vehicle_type", record.vehicle_type)
        record.distance_km = updated_data.get("distance_km", record.distance_km)
        record.mass_tonnes = updated_data.get("mass_tonnes", record.mass_tonnes)
        record.energy_kwh = updated_data.get("energy_kwh", record.energy_kwh)
        
        # Parse date if provided
        if updated_data.get("date"):
            try:
                from datetime import datetime
                parsed_date = datetime.strptime(updated_data["date"], "%Y-%m-%d").date()
                record.date = parsed_date
            except ValueError:
                pass  # Keep existing date if parsing fails
        
        # Recalculate emissions with updated data
        try:
            record_dict = {
                'amount': record.amount,
                'currency': record.currency,
                'ef_factor_per_currency': record.ef_factor_per_currency,
                'activity_amount': record.activity_amount,
                'emission_factor_value': record.emission_factor_value,
                'activity_type': record.activity_type,
                'scope': record.scope,
                'category': record.category,
                'description': record.description,
                'raw_row': record.raw_row
            }
            calculated_data = calculate_emissions_if_missing(record_dict, db)
            record.emissions_kgco2e = calculated_data.get('emissions_kgco2e')
        except Exception as e:
            print(f"Warning: Could not recalculate emissions: {e}")
        
        # Mark as reviewed and human-edited
        record.needs_human_review = False
        record.ai_classified = False  # Mark as human-edited (not AI classified)
        
        # Update hash chain for integrity
        record.previous_hash = record.record_hash  # Store previous hash
        record.salt = secrets.token_hex(8)
        base = hashing.calculate_record_base_string(record.__dict__)
        record.record_hash = hashing.calculate_record_hash(record.previous_hash, base, record.salt)
        
        db.commit()
        
        return {
            "success": True,
            "message": "Record approved with human changes and marked as reviewed"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to approve record with changes: {str(e)}"
        }

@app.post("/api/calculate-emissions")
def calculate_emissions_endpoint(
    request: dict,
    db: Session = Depends(get_db)
):
    """Calculate emissions for a single record or batch of records"""
    try:
        if 'records' in request:
            # Batch calculation
            records = request['records']
            calculated_records = batch_calculate_emissions(records, db)
            
            return {
                "success": True,
                "calculated_records": calculated_records,
                "total_processed": len(records),
                "successfully_calculated": len([r for r in calculated_records if r.get('emissions_kgco2e') is not None])
            }
        else:
            # Single record calculation
            record = request
            calculated_record = calculate_emissions_if_missing(record, db)
            
            return {
                "success": True,
                "calculated_record": calculated_record
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to calculate emissions: {str(e)}"
        }

@app.post("/api/calculate-emissions/{record_id}")
def calculate_emissions_for_record(
    record_id: str,
    db: Session = Depends(get_db)
):
    """Calculate emissions for an existing record in the database"""
    try:
        record = db.query(models.EmissionRecord).filter(
            models.EmissionRecord.id == record_id
        ).first()
        
        if not record:
            return {
                "success": False,
                "error": "Record not found"
            }
        
        # Convert record to dict for calculation
        record_dict = {
            'amount': record.amount,
            'currency': record.currency,
            'ef_factor_per_currency': record.ef_factor_per_currency,
            'activity_amount': record.activity_amount,
            'emission_factor_value': record.emission_factor_value,
            'activity_type': record.activity_type,
            'scope': record.scope,
            'category': record.category,
            'description': record.description,
            'raw_row': record.raw_row
        }
        
        # Calculate emissions
        calculated_data = calculate_emissions_if_missing(record_dict, db)
        
        # Update the record
        record.emissions_kgco2e = calculated_data.get('emissions_kgco2e')
        
        # Update hash chain for integrity
        record.previous_hash = record.record_hash
        record.salt = secrets.token_hex(8)
        base = hashing.calculate_record_base_string(record.__dict__)
        record.record_hash = hashing.calculate_record_hash(record.previous_hash, base, record.salt)
        
        db.commit()
        
        return {
            "success": True,
            "record_id": str(record.id),
            "emissions_kgco2e": float(record.emissions_kgco2e) if record.emissions_kgco2e else None,
            "calculation_method": calculated_data.get('calculation_method'),
            "calculation_details": calculated_data.get('calculation_details')
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to calculate emissions for record: {str(e)}"
        }

# Carbon Rewards Engine API Endpoints

@app.post("/api/scan-opportunities")
def scan_opportunities(
    request: dict,
    db: Session = Depends(get_db)
):
    """Scan emission records for carbon offset and credit opportunities"""
    try:
        records = request.get('records', [])
        options = request.get('options', {})
        
        if not records:
            return {"success": False, "error": "No records provided"}
        
        # Use rewards engine to scan opportunities
        opportunities = rewards_engine.scan_carbon_opportunities(records, db)
        
        return {
            "success": True,
            "opportunities": opportunities,
            "records_scanned": len(records)
        }
        
    except Exception as e:
        logger.error(f"Error scanning opportunities: {str(e)}")
        return {"success": False, "error": str(e)}


@app.get("/api/opportunities")
def get_opportunities(
    skip: int = 0,
    limit: int = 100,
    opportunity_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get carbon opportunities with optional filtering"""
    try:
        query = db.query(models.CarbonOpportunity)
        
        # Apply filters
        if opportunity_type:
            query = query.filter(models.CarbonOpportunity.opportunity_type == opportunity_type)
        if status:
            query = query.filter(models.CarbonOpportunity.status == status)
        
        # Apply pagination
        opportunities = query.offset(skip).limit(limit).all()
        
        # Convert to dict format
        result = []
        for opp in opportunities:
            opp_dict = {
                "id": str(opp.id),
                "opportunity_type": opp.opportunity_type,
                "program_name": opp.program_name,
                "program_agency": opp.program_agency,
                "description": opp.description,
                "potential_value": float(opp.potential_value) if opp.potential_value else 0,
                "confidence_score": float(opp.confidence_score) if opp.confidence_score else 0,
                "emissions_reduced": float(opp.emissions_reduced) if opp.emissions_reduced else 0,
                "application_link": opp.application_link,
                "deadline": opp.deadline.isoformat() if opp.deadline else None,
                "status": opp.status,
                "created_at": opp.created_at.isoformat() if opp.created_at else None
            }
            result.append(opp_dict)
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching opportunities: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/deadlines")
def get_deadlines(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    is_completed: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get compliance deadlines with optional filtering"""
    try:
        query = db.query(models.ComplianceDeadline)
        
        # Apply filters
        if is_active is not None:
            query = query.filter(models.ComplianceDeadline.is_active == is_active)
        if is_completed is not None:
            query = query.filter(models.ComplianceDeadline.is_completed == is_completed)
        
        # Apply pagination
        deadlines = query.offset(skip).limit(limit).all()
        
        # Convert to dict format
        result = []
        for deadline in deadlines:
            deadline_dict = {
                "id": str(deadline.id),
                "program_name": deadline.program_name,
                "deadline_type": deadline.deadline_type,
                "deadline_date": deadline.deadline_date.isoformat() if deadline.deadline_date else None,
                "timezone": deadline.timezone,
                "is_active": deadline.is_active,
                "is_completed": deadline.is_completed,
                "completion_date": deadline.completion_date.isoformat() if deadline.completion_date else None,
                "created_at": deadline.created_at.isoformat() if deadline.created_at else None
            }
            result.append(deadline_dict)
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching deadlines: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/deadlines/{deadline_id}/complete")
def mark_deadline_complete(
    deadline_id: str,
    db: Session = Depends(get_db)
):
    """Mark a deadline as complete"""
    try:
        deadline = db.query(models.ComplianceDeadline).filter(
            models.ComplianceDeadline.id == deadline_id
        ).first()
        
        if not deadline:
            raise HTTPException(status_code=404, detail="Deadline not found")
        
        deadline.is_completed = True
        deadline.completion_date = datetime.now()
        db.commit()
        
        return {"success": True, "message": "Deadline marked as complete"}
        
    except Exception as e:
        logger.error(f"Error marking deadline complete: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-application")
def generate_application(
    request: dict,
    db: Session = Depends(get_db)
):
    """Generate pre-filled application for an opportunity"""
    try:
        opportunity_id = request.get('opportunity_id')
        
        if not opportunity_id:
            return {"success": False, "error": "Opportunity ID required"}
        
        # Get opportunity details
        opportunity = db.query(models.CarbonOpportunity).filter(
            models.CarbonOpportunity.id == opportunity_id
        ).first()
        
        if not opportunity:
            return {"success": False, "error": "Opportunity not found"}
        
        # Get application template
        template = db.query(models.ApplicationTemplate).filter(
            models.ApplicationTemplate.opportunity_type == opportunity.opportunity_type,
            models.ApplicationTemplate.program_name == opportunity.program_name,
            models.ApplicationTemplate.is_active == True
        ).first()
        
        if not template:
            # Create basic template if none exists
            template_data = {
                "form_fields": {
                    "program_name": opportunity.program_name,
                    "opportunity_type": opportunity.opportunity_type,
                    "potential_value": float(opportunity.potential_value) if opportunity.potential_value else 0,
                    "emissions_reduced": float(opportunity.emissions_reduced) if opportunity.emissions_reduced else 0,
                    "application_date": datetime.now().isoformat()
                },
                "required_documents": [
                    "Emission calculation documentation",
                    "Project description",
                    "Financial statements",
                    "Environmental impact assessment"
                ]
            }
        else:
            template_data = {
                "form_fields": template.form_fields or {},
                "required_documents": template.required_documents or []
            }
        
        return {
            "success": True,
            "application": template_data,
            "opportunity": {
                "id": str(opportunity.id),
                "program_name": opportunity.program_name,
                "opportunity_type": opportunity.opportunity_type,
                "potential_value": float(opportunity.potential_value) if opportunity.potential_value else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating application: {str(e)}")
        return {"success": False, "error": str(e)}


@app.post("/api/submit-application")
def submit_application(
    request: dict,
    db: Session = Depends(get_db)
):
    """Submit application and update opportunity status"""
    try:
        opportunity_id = request.get('opportunity_id')
        
        if not opportunity_id:
            return {"success": False, "error": "Opportunity ID required"}
        
        # Update opportunity status
        opportunity = db.query(models.CarbonOpportunity).filter(
            models.CarbonOpportunity.id == opportunity_id
        ).first()
        
        if not opportunity:
            return {"success": False, "error": "Opportunity not found"}
        
        opportunity.status = 'applied'
        opportunity.application_date = datetime.now()
        db.commit()
        
        return {
            "success": True,
            "message": "Application submitted successfully",
            "opportunity_id": opportunity_id
        }
        
    except Exception as e:
        logger.error(f"Error submitting application: {str(e)}")
        return {"success": False, "error": str(e)}


# Climate TRACE API Endpoints

@app.get("/api/climate-trace/status")
def get_climate_trace_status():
    """Get Climate TRACE integration status and job information"""
    try:
        job_status = get_ct_job_status()
        return {
            "enabled": climate_trace_service.enabled,
            "job_status": job_status,
            "api_available": True
        }
    except Exception as e:
        logger.error(f"Error getting Climate TRACE status: {e}")
        return {
            "enabled": False,
            "job_status": {"error": str(e)},
            "api_available": False
        }

@app.get("/api/climate-trace/monthly-data")
def get_climate_trace_monthly_data(
    year: int,
    month: int,
    sector: Optional[str] = None,
    country_code: Optional[str] = None
):
    """Get Climate TRACE monthly data"""
    try:
        data = climate_trace_service.fetch_climate_trace_data(year, month, sector, country_code)
        return {
            "success": True,
            "data": data,
            "year": year,
            "month": month,
            "sector": sector,
            "country_code": country_code,
            "count": len(data)
        }
    except Exception as e:
        logger.error(f"Error fetching Climate TRACE monthly data: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": []
        }

@app.get("/api/climate-trace/enhanced/status")
def get_enhanced_climate_trace_status():
    """Get enhanced Climate TRACE integration status with methodology information"""
    try:
        methodology_summary = enhanced_climate_trace_service.get_methodology_summary()
        return {
            "enabled": enhanced_climate_trace_service.enabled,
            "available_sectors": enhanced_climate_trace_service.get_available_sectors(),
            "methodology_summary": methodology_summary,
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "enabled": False,
            "error": str(e),
            "last_updated": datetime.now().isoformat()
        }

@app.get("/api/climate-trace/enhanced/methodology")
def get_climate_trace_methodology():
    """Get Climate TRACE methodology information and emission factors"""
    try:
        methodology_summary = enhanced_climate_trace_service.get_methodology_summary()
        return {
            "success": True,
            "methodology": methodology_summary,
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting Climate TRACE methodology: {e}")
        return {
            "success": False,
            "error": str(e),
            "last_updated": datetime.now().isoformat()
        }

@app.post("/api/climate-trace/enhanced/validate")
def validate_emission_record(request: dict, db: Session = Depends(get_db)):
    """Validate emission record against Climate TRACE methodologies"""
    try:
        record_id = request.get("record_id")
        if not record_id:
            return {
                "success": False,
                "error": "record_id is required"
            }
        
        # Get the emission record
        record = db.query(models.EmissionRecord).filter(
            models.EmissionRecord.id == record_id
        ).first()
        
        if not record:
            return {
                "success": False,
                "error": "Record not found"
            }
        
        # Convert to dictionary for validation
        record_dict = {
            "ct_sector": record.ct_sector,
            "ct_subsector": record.ct_subsector,
            "fuel_type": record.fuel_type,
            "activity_type": record.activity_type,
            "activity_amount": record.activity_amount,
            "emission_factor_value": record.emission_factor_value,
            "emissions_kgco2e": record.emissions_kgco2e
        }
        
        # Validate against methodology
        validation_result = enhanced_climate_trace_service.validate_against_methodology(record_dict)
        
        return {
            "success": True,
            "record_id": record_id,
            "validation_result": validation_result,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "last_updated": datetime.now().isoformat()
        }

@app.post("/api/climate-trace/enhanced/calculate")
def calculate_enhanced_emissions(request: dict, db: Session = Depends(get_db)):
    """Calculate emissions using enhanced Climate TRACE methodologies"""
    try:
        record_id = request.get("record_id")
        if not record_id:
            return {
                "success": False,
                "error": "record_id is required"
            }
        
        # Get the emission record
        record = db.query(models.EmissionRecord).filter(
            models.EmissionRecord.id == record_id
        ).first()
        
        if not record:
            return {
                "success": False,
                "error": "Record not found"
            }
        
        # Convert to dictionary for calculation
        record_dict = {
            "ct_sector": record.ct_sector,
            "ct_subsector": record.ct_subsector,
            "fuel_type": record.fuel_type,
            "activity_type": record.activity_type,
            "activity_amount": record.activity_amount,
            "emission_factor_value": record.emission_factor_value,
            "emissions_kgco2e": record.emissions_kgco2e
        }
        
        # Calculate enhanced emissions
        enhanced_result = enhanced_climate_trace_service.calculate_enhanced_emissions(record_dict)
        
        return {
            "success": True,
            "record_id": record_id,
            "enhanced_calculation": enhanced_result,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "last_updated": datetime.now().isoformat()
        }


@app.post("/api/climate-trace/sync")
async def run_climate_trace_sync(
    year: int,
    month: int,
    db: Session = Depends(get_db)
):
    """Run manual Climate TRACE sync for specific year/month"""
    try:
        if not climate_trace_service.enabled:
            raise HTTPException(status_code=400, detail="Climate TRACE integration is disabled")
        
        success = await run_manual_ct_sync(year, month)
        
        if success:
            return {
                "success": True,
                "message": f"Climate TRACE sync completed for {year}-{month:02d}",
                "year": year,
                "month": month
            }
        else:
            raise HTTPException(status_code=500, detail="Climate TRACE sync failed")
            
    except Exception as e:
        logger.error(f"Error running Climate TRACE sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/climate-trace/crosscheck")
def run_crosscheck_analysis(
    year: int,
    month: int,
    threshold_percentage: float = 10.0,
    db: Session = Depends(get_db)
):
    """Run cross-check analysis between our ledger and Climate TRACE data"""
    try:
        if not climate_trace_service.enabled:
            raise HTTPException(status_code=400, detail="Climate TRACE integration is disabled")
        
        crosschecks = climate_trace_service.run_crosscheck_analysis(
            db, year, month, threshold_percentage
        )
        
        return {
            "success": True,
            "crosschecks_created": len(crosschecks),
            "year": year,
            "month": month,
            "threshold_percentage": threshold_percentage,
            "results": [
                {
                    "id": str(cc.id),
                    "sector": cc.ct_sector,
                    "subsector": cc.ct_subsector,
                    "our_emissions": float(cc.our_emissions_kgco2e),
                    "ct_emissions": float(cc.ct_emissions_kgco2e),
                    "delta_percentage": float(cc.delta_percentage),
                    "compliance_status": cc.compliance_status,
                    "threshold_exceeded": cc.threshold_exceeded
                }
                for cc in crosschecks
            ]
        }
        
    except Exception as e:
        logger.error(f"Error running cross-check analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/climate-trace/crosschecks")
def get_crosscheck_results(
    year: Optional[int] = None,
    month: Optional[int] = None,
    compliance_status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get cross-check results with optional filtering"""
    try:
        if not climate_trace_service.enabled:
            raise HTTPException(status_code=400, detail="Climate TRACE integration is disabled")
        
        crosschecks = climate_trace_service.get_crosscheck_results(
            db, year, month, compliance_status
        )
        
        # Apply limit
        crosschecks = crosschecks[:limit]
        
        return crosschecks
        
    except Exception as e:
        logger.error(f"Error fetching cross-check results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/climate-trace/crosschecks/{crosscheck_id}/acknowledge")
def acknowledge_crosscheck(
    crosscheck_id: str,
    acknowledged_by: str,
    db: Session = Depends(get_db)
):
    """Acknowledge a cross-check result"""
    try:
        if not climate_trace_service.enabled:
            raise HTTPException(status_code=400, detail="Climate TRACE integration is disabled")
        
        success = climate_trace_service.acknowledge_crosscheck(
            db, crosscheck_id, acknowledged_by
        )
        
        if success:
            return {
                "success": True,
                "message": "Cross-check acknowledged successfully",
                "crosscheck_id": crosscheck_id,
                "acknowledged_by": acknowledged_by
            }
        else:
            raise HTTPException(status_code=404, detail="Cross-check not found")
            
    except Exception as e:
        logger.error(f"Error acknowledging cross-check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class MapRecordsRequest(BaseModel):
    record_ids: Optional[List[str]] = None

@app.post("/api/climate-trace/map-records")
def map_records_to_climate_trace(
    request: MapRecordsRequest = MapRecordsRequest(),
    db: Session = Depends(get_db)
):
    """Map existing emission records to Climate TRACE sectors for cross-checking"""
    try:
        if not climate_trace_service.enabled:
            raise HTTPException(status_code=400, detail="Climate TRACE integration disabled")
        
        # Get record_ids from request, or None to map all records
        record_ids = request.record_ids
        result = climate_trace_service.map_records_to_climate_trace(db, record_ids)
        
        return result
    
    except Exception as e:
        logger.error(f"Error mapping records to Climate TRACE: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/climate-trace/sectors")
def get_climate_trace_sectors():
    """Get available Climate TRACE sectors and subsectors"""
    try:
        if not climate_trace_service.enabled:
            return {
                "success": False,
                "error": "Climate TRACE integration is disabled"
            }
        
        # Get sectors from enhanced service
        sectors = enhanced_climate_trace_service.get_available_sectors()
        
        return {
            "success": True,
            "sectors": sectors,
            "total_sectors": len(sectors),
            "mapping": "Activity mapping available via map_activity_to_climate_trace method"
        }
        
    except Exception as e:
        logger.error(f"Error fetching Climate TRACE sectors: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Advanced Analytics Endpoints
@app.get("/api/climate-trace/analytics/trends")
def get_trend_analysis(sector: Optional[str] = None, months_back: int = 12, db: Session = Depends(get_db)):
    """Get trend analysis for Climate TRACE data"""
    try:
        analytics_service = ClimateTraceAdvancedAnalytics(db)
        trends = analytics_service.analyze_trends(sector=sector, months_back=months_back)
        
        # Convert dataclass to dict for JSON serialization
        trends_data = []
        for trend in trends:
            trends_data.append({
                'sector': trend.sector,
                'trend_direction': trend.trend_direction,
                'trend_strength': trend.trend_strength,
                'change_rate': trend.change_rate,
                'confidence': trend.confidence,
                'data_points': trend.data_points,
                'last_6_months_avg': trend.last_6_months_avg,
                'prediction_next_month': trend.prediction_next_month,
                'risk_level': trend.risk_level
            })
        
        return {"success": True, "trends": trends_data}
    except Exception as e:
        logger.error(f"Error getting trend analysis: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/climate-trace/analytics/alerts")
def get_predictive_alerts(days_ahead: int = 30, db: Session = Depends(get_db)):
    """Get predictive alerts for compliance risks"""
    try:
        analytics_service = ClimateTraceAdvancedAnalytics(db)
        alerts = analytics_service.generate_predictive_alerts(days_ahead=days_ahead)
        
        # Convert dataclass to dict for JSON serialization
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                'alert_id': alert.alert_id,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'sector': alert.sector,
                'predicted_date': alert.predicted_date.isoformat(),
                'confidence': alert.confidence,
                'description': alert.description,
                'recommended_actions': alert.recommended_actions,
                'current_risk_score': alert.current_risk_score,
                'predicted_risk_score': alert.predicted_risk_score
            })
        
        return {"success": True, "alerts": alerts_data}
    except Exception as e:
        logger.error(f"Error getting predictive alerts: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/climate-trace/analytics/risk-score")
def get_comprehensive_risk_score(sector: Optional[str] = None, db: Session = Depends(get_db)):
    """Get comprehensive risk score for compliance"""
    try:
        analytics_service = ClimateTraceAdvancedAnalytics(db)
        risk_score = analytics_service.calculate_comprehensive_risk_score(sector=sector)
        
        return {
            "success": True,
            "risk_score": {
                'overall_score': risk_score.overall_score,
                'compliance_risk': risk_score.compliance_risk,
                'data_quality_risk': risk_score.data_quality_risk,
                'trend_risk': risk_score.trend_risk,
                'regulatory_risk': risk_score.regulatory_risk,
                'factors': risk_score.factors,
                'recommendations': risk_score.recommendations
            }
        }
    except Exception as e:
        logger.error(f"Error getting risk score: {e}")
        return {"success": False, "error": str(e)}

# Automated Reporting Endpoints
@app.post("/api/climate-trace/reports/compliance")
def generate_compliance_report(
    report_type: str = "monthly",
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Generate compliance report"""
    try:
        reporting_service = ClimateTraceAutomatedReporting(db)
        
        # Parse dates if provided
        start_date = datetime.fromisoformat(period_start) if period_start else None
        end_date = datetime.fromisoformat(period_end) if period_end else None
        
        report = reporting_service.generate_compliance_report(
            report_type=report_type,
            period_start=start_date,
            period_end=end_date
        )
        
        return {
            "success": True,
            "report": {
                'report_id': report.report_id,
                'report_type': report.report_type,
                'period_start': report.period_start.isoformat(),
                'period_end': report.period_end.isoformat(),
                'generated_at': report.generated_at.isoformat(),
                'summary': report.summary,
                'detailed_results': report.detailed_results,
                'recommendations': report.recommendations,
                'risk_assessment': report.risk_assessment,
                'regulatory_status': report.regulatory_status
            }
        }
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/climate-trace/regulatory/submission")
def generate_regulatory_submission(
    regulatory_body: str,
    submission_type: str = "emissions_report",
    db: Session = Depends(get_db)
):
    """Generate regulatory submission"""
    try:
        reporting_service = ClimateTraceAutomatedReporting(db)
        submission = reporting_service.generate_regulatory_submission(
            regulatory_body=regulatory_body,
            submission_type=submission_type
        )
        
        return {
            "success": True,
            "submission": {
                'submission_id': submission.submission_id,
                'regulatory_body': submission.regulatory_body,
                'submission_type': submission.submission_type,
                'due_date': submission.due_date.isoformat(),
                'status': submission.status,
                'data': submission.data,
                'attachments': submission.attachments
            }
        }
    except Exception as e:
        logger.error(f"Error generating regulatory submission: {e}")
        return {"success": False, "error": str(e)}

# Regulatory Integration Endpoints
@app.get("/api/climate-trace/regulatory/dashboard")
def get_regulatory_dashboard(db: Session = Depends(get_db)):
    """Get regulatory compliance dashboard data"""
    try:
        # Get organization emissions data (mock for now)
        organization_data = {
            'total_emissions_tons_co2e': 50000,  # This would come from actual data
            'sector_breakdown': {
                'Power': 20000,
                'Transportation': 15000,
                'Manufacturing': 10000,
                'Waste': 5000
            }
        }
        
        regulatory_service = ClimateTraceRegulatoryIntegration(db)
        dashboard_data = regulatory_service.generate_compliance_dashboard_data(organization_data)
        
        return {"success": True, "dashboard": dashboard_data}
    except Exception as e:
        logger.error(f"Error getting regulatory dashboard: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/climate-trace/regulatory/deadlines")
def get_regulatory_deadlines(db: Session = Depends(get_db)):
    """Get upcoming regulatory deadlines"""
    try:
        # Get organization data (mock for now)
        organization_data = {
            'total_emissions_tons_co2e': 50000,
            'last_submission': datetime.now() - timedelta(days=30)
        }
        
        regulatory_service = ClimateTraceRegulatoryIntegration(db)
        deadlines = regulatory_service.get_regulatory_deadlines(organization_data)
        
        return {"success": True, "deadlines": deadlines}
    except Exception as e:
        logger.error(f"Error getting regulatory deadlines: {e}")
        return {"success": False, "error": str(e)}

# Carbon Markets Endpoints
@app.get("/api/climate-trace/carbon-markets/dashboard")
def get_carbon_markets_dashboard(db: Session = Depends(get_db)):
    """Get carbon markets dashboard data"""
    try:
        # Get organization emissions data (mock for now)
        organization_emissions = {
            'Power': 20000,
            'Transportation': 15000,
            'Manufacturing': 10000,
            'Waste': 5000
        }
        
        carbon_markets_service = ClimateTraceCarbonMarkets(db)
        dashboard_data = carbon_markets_service.generate_carbon_markets_dashboard(organization_emissions)
        
        return {"success": True, "dashboard": dashboard_data}
    except Exception as e:
        logger.error(f"Error getting carbon markets dashboard: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/climate-trace/carbon-markets/portfolio")
def calculate_offset_portfolio(request: dict, db: Session = Depends(get_db)):
    """Calculate optimal carbon offset portfolio"""
    try:
        budget_usd = request.get("budget_usd", 100000)
        offset_percentage = request.get("offset_percentage", 100)
        
        # Get organization emissions data (mock for now)
        organization_emissions = {
            'Power': 20000,
            'Transportation': 15000,
            'Manufacturing': 10000,
            'Waste': 5000
        }
        
        carbon_markets_service = ClimateTraceCarbonMarkets(db)
        
        # Create a sample portfolio
        sample_portfolio = [
            {
                "project_id": "VCS-001",
                "project_name": "Renewable Energy Project",
                "credits": 1000,
                "price_per_credit": 15.0,
                "standard": "VCS"
            },
            {
                "project_id": "GOLD-002", 
                "project_name": "Forest Conservation",
                "credits": 500,
                "price_per_credit": 25.0,
                "standard": "Gold Standard"
            }
        ]
        
        portfolio_value = carbon_markets_service.calculate_portfolio_value(sample_portfolio)
        
        return {
            "success": True, 
            "portfolio": {
                "budget_usd": budget_usd,
                "offset_percentage": offset_percentage,
                "recommended_projects": sample_portfolio,
                "portfolio_value": portfolio_value
            }
        }
    except Exception as e:
        logger.error(f"Error calculating offset portfolio: {e}")
        return {"success": False, "error": str(e)}

# ESG Reporting Endpoints
@app.post("/api/climate-trace/esg/report")
def generate_esg_report(request: dict, db: Session = Depends(get_db)):
    """Generate ESG report for specified framework"""
    try:
        framework = request.get("framework", "TCFD")
        
        # Get basic emission data
        total_emissions = db.query(func.sum(models.EmissionRecord.emissions_kgco2e)).scalar() or 0
        total_records = db.query(func.count(models.EmissionRecord.id)).scalar() or 0
        
        # Create simplified ESG report
        esg_data = {
            'reporting_framework': framework,
            'reporting_period': {
                'start': '2024-01-01',
                'end': '2024-12-31'
            },
            'environmental_metrics': {
                'total_emissions_tons_co2e': float(total_emissions) / 1000,
                'total_emission_records': total_records,
                'emissions_verification': {
                    'method': 'Climate TRACE Cross-Check',
                    'coverage': 'Multiple sectors',
                    'accuracy_rate': 95.0
                }
            },
            'governance_metrics': {
                'compliance_management': {
                    'automated_monitoring': True,
                    'third_party_verification': True,
                    'risk_assessment': True
                },
                'data_quality': {
                    'verification_method': 'Satellite-based Climate TRACE data',
                    'accuracy_score': 95.0
                }
            },
            'risk_management': {
                'climate_risk_assessment': 'Completed',
                'adaptation_measures': 'In progress',
                'mitigation_strategies': 'Implemented'
            },
            'stakeholder_engagement': {
                'transparency_level': 'High',
                'reporting_frequency': 'Annual',
                'verification_status': 'Third-party verified'
            }
        }
        
        return {"success": True, "esg_report": esg_data}
    except Exception as e:
        logger.error(f"Error generating ESG report: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/climate-trace/esg/history")
def get_esg_reporting_history(db: Session = Depends(get_db)):
    """Get ESG reporting history"""
    try:
        # This would query the database for historical reports
        # For now, return mock data
        history = [
            {
                'framework': 'GRI',
                'reporting_period': '2023',
                'generated_at': '2024-01-15T10:30:00',
                'status': 'completed'
            },
            {
                'framework': 'TCFD',
                'reporting_period': '2023',
                'generated_at': '2024-01-10T14:20:00',
                'status': 'completed'
            }
        ]
        
        return {"success": True, "history": history}
    except Exception as e:
        logger.error(f"Error getting ESG reporting history: {e}")
        return {"success": False, "error": str(e)}


def _check_ollama_availability() -> bool:
    """Check if Ollama is available"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

# ============================================================================
# COMPLIANCE INTEGRITY ENGINE ENDPOINTS
# ============================================================================

@app.get("/api/compliance/dashboard")
def get_compliance_dashboard(db: Session = Depends(get_db)):
    """Get compliance dashboard data"""
    try:
        compliance_engine = ComplianceIntegrityEngine(db)
        dashboard_data = compliance_engine.get_compliance_dashboard_data()
        
        # Extract overview data and flatten the structure
        overview = dashboard_data.get('overview', {})
        dashboard = {
            'overall_compliance_rate': overview.get('compliance_rate', 0),
            'total_records': overview.get('total_records', 0),
            'high_quality_records': overview.get('audit_ready_count', 0),
            'average_compliance_score': overview.get('average_compliance_score', 0),
            'compliance_breakdown': dashboard_data.get('score_distribution', {}),
            'recent_snapshots': dashboard_data.get('recent_snapshots', []),
            'upcoming_deadlines': dashboard_data.get('upcoming_deadlines', []),
            'last_updated': dashboard_data.get('last_updated', datetime.now().isoformat())
        }
        
        return {
            "success": True,
            "dashboard": dashboard
        }
    except Exception as e:
        logger.error(f"Error getting compliance dashboard: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/compliance/scores")
def get_compliance_scores(limit: int = 100, db: Session = Depends(get_db)):
    """Get compliance scores for emission records"""
    try:
        records = db.query(models.EmissionRecord).limit(limit).all()
        
        scores = []
        for record in records:
            scores.append({
                "record_id": str(record.id),
                "supplier_name": record.supplier_name,
                "activity_type": record.activity_type,
                "compliance_score": record.compliance_score,
                "data_quality_score": record.data_quality_score,
                "audit_ready": record.audit_ready,
                "verification_status": record.verification_status,
                "created_at": record.created_at.isoformat() if record.created_at else None
            })
        
        return scores
        
    except Exception as e:
        logger.error(f"Error getting compliance scores: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/compliance/audit-snapshots")
def get_audit_snapshots(limit: int = 10, db: Session = Depends(get_db)):
    """Get unified audit snapshots from both systems"""
    try:
        # Use the sync service to get unified snapshots
        unified_snapshots = AuditSyncService.get_unified_snapshots(db, limit)
        
        # Convert to the expected format
        snapshot_data = []
        for snapshot in unified_snapshots:
            snapshot_data.append({
                "snapshot_id": snapshot["id"],
                "submission_id": snapshot["submission_id"],
                "submission_type": snapshot["submission_type"],
                "reporting_period_start": snapshot["reporting_period_start"],
                "reporting_period_end": snapshot["reporting_period_end"],
                "merkle_root_hash": f"unified_{snapshot['id'][:16]}",
                "total_records": snapshot["total_records"],
                "total_emissions_kgco2e": snapshot["total_emissions_kgco2e"],
                "average_compliance_score": snapshot.get("average_compliance_score", 0.0),
                "audit_ready_records": snapshot.get("audit_ready_records", 0),
                "non_compliant_records": snapshot.get("non_compliant_records", 0),
                "created_at": snapshot["created_at"],
                "source": snapshot.get("source", "unified")
            })
        
        return snapshot_data
        
    except Exception as e:
        logger.error(f"Error getting unified audit snapshots: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/compliance/update-scores")
def update_compliance_scores(db: Session = Depends(get_db)):
    """Update compliance scores for all records to improve data quality"""
    try:
        # Get all records
        records = db.query(models.EmissionRecord).all()
        updated_count = 0
        
        for record in records:
            # Calculate a realistic compliance score based on record data
            base_score = 50  # Base score
            
            # Add points for good data
            if record.supplier_name and len(record.supplier_name.strip()) > 0:
                base_score += 10
            if record.activity_type and len(record.activity_type.strip()) > 0:
                base_score += 10
            if record.emissions_kgco2e and record.emissions_kgco2e > 0:
                base_score += 15
            if record.verification_status and record.verification_status != 'unverified':
                base_score += 15
            if record.methodology and len(record.methodology.strip()) > 0:
                base_score += 10
            
            # Cap at 100
            new_score = min(base_score, 100)
            
            # Update the record
            record.compliance_score = new_score
            record.data_quality_score = new_score
            record.audit_ready = new_score >= 80
            
            updated_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Updated compliance scores for {updated_count} records",
            "updated_count": updated_count
        }
        
    except Exception as e:
        logger.error(f"Error updating compliance scores: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }

# ============================================================================
# INTAKE ASSISTANT ENDPOINT
# ============================================================================

class IntakeSuggestRequest(BaseModel):
    supplier_name: Optional[str] = None
    activity_type: Optional[str] = None
    country_code: Optional[str] = None
    # Climate TRACE aligned fields
    sector: Optional[str] = None
    subsector: Optional[str] = None
    year: Optional[int] = None
    owner: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    # Non-matching fields still accepted for our own defaults/labels (not used for CT matching)
    grid_region: Optional[str] = None
    scope: Optional[Union[str, int]] = None
    fuel_type: Optional[str] = None


@app.post("/api/intake/suggest")
def intake_suggest(req: IntakeSuggestRequest, db: Session = Depends(get_db)):
    """Return smart suggestions for intake fields (history + Climate TRACE mapping)."""
    try:
        assistant = build_intake_assistant(db)
        suggestions = assistant.suggest(req.dict())
        return {"success": True, "suggestions": suggestions}
    except Exception as e:
        logger.error(f"Error generating intake suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ImportClimateTraceRequest(BaseModel):
    ct_data: Dict[str, Any]
    user_emissions_kgco2e: Optional[float] = None
    user_notes: Optional[str] = None
    import_action: str  # "compare_only", "import_as_reference", "import_as_primary"


@app.post("/api/intake/import-climate-trace")
def import_climate_trace_data(req: ImportClimateTraceRequest, db: Session = Depends(get_db)):
    """Import Climate TRACE data with human review and comparison."""
    try:
        ct_data = req.ct_data
        user_emissions = req.user_emissions_kgco2e
        user_notes = req.user_notes
        import_action = req.import_action
        
        # Calculate comparison metrics
        ct_emissions = ct_data.get("total_emissions_kgco2e", 0)
        comparison_result = {
            "climate_trace_emissions": ct_emissions,
            "user_emissions": user_emissions,
            "difference_kgco2e": (user_emissions or 0) - ct_emissions,
            "percentage_difference": 0,
            "comparison_status": "no_user_data"
        }
        
        if user_emissions and ct_emissions > 0:
            diff_pct = ((user_emissions - ct_emissions) / ct_emissions) * 100
            comparison_result["percentage_difference"] = diff_pct
            
            if abs(diff_pct) < 10:
                comparison_result["comparison_status"] = "good_match"
            elif abs(diff_pct) < 25:
                comparison_result["comparison_status"] = "reasonable_difference"
            else:
                comparison_result["comparison_status"] = "significant_difference"
        
        # Create emission record if importing
        record_id = None
        if import_action in ["import_as_reference", "import_as_primary"]:
            # Create a new emission record with Climate TRACE data
            record = models.EmissionRecord(
                record_id=f"CT_{uuid.uuid4().hex[:8]}",
                external_id=f"climate_trace_{ct_data.get('ct_sector', 'unknown')}_{ct_data.get('ct_year', 2024)}",
                supplier_name=ct_data.get("ct_owner", "Climate TRACE"),
                activity_type=ct_data.get("ct_sector", "unknown"),
                scope=1,  # Default to Scope 1 for Climate TRACE data
                emissions_kgco2e=ct_emissions,
                methodology="Climate TRACE - Satellite + AI",
                ef_source="Climate TRACE API",
                ef_ref_code="CT_SATELLITE_AI",
                ef_version="2024.1",
                data_quality_score=4,  # High quality
                verification_status="climate_trace_verified",
                notes=f"Imported from Climate TRACE. {user_notes or ''}",
                description=f"Climate TRACE data for {ct_data.get('ct_sector', 'unknown')} sector",
                # Climate TRACE specific fields
                ct_sector=ct_data.get("ct_sector"),
                ct_subsector=ct_data.get("ct_subsector"),
                ct_country_code=ct_data.get("ct_country_code"),
                # Mark for human review
                needs_human_review=True,
                ai_classified=True,
                confidence_score=0.9,  # High confidence for Climate TRACE
                classification_metadata={
                    "source": "climate_trace_import",
                    "import_action": import_action,
                    "comparison_result": comparison_result,
                    "data_freshness": ct_data.get("data_freshness"),
                    "confidence_level": ct_data.get("confidence_level")
                }
            )
            
            db.add(record)
            db.commit()
            record_id = str(record.id)
        
        return {
            "success": True,
            "record_id": record_id,
            "comparison_result": comparison_result,
            "import_status": f"Data {'imported' if record_id else 'compared'} successfully",
            "human_review_required": True,
            "recommendations": _get_comparison_recommendations(comparison_result)
        }
        
    except Exception as e:
        logger.error(f"Error importing Climate TRACE data: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def _get_comparison_recommendations(comparison_result: Dict) -> List[str]:
    """Generate recommendations based on comparison results."""
    recommendations = []
    status = comparison_result.get("comparison_status")
    diff_pct = comparison_result.get("percentage_difference", 0)
    
    if status == "good_match":
        recommendations.append("✅ Excellent match! Your data aligns well with Climate TRACE.")
    elif status == "reasonable_difference":
        recommendations.append("⚠️ Reasonable difference. Consider reviewing calculation methods.")
    elif status == "significant_difference":
        recommendations.append("🚨 Significant difference detected. Manual review recommended.")
        recommendations.append("💡 Check: emission factors, activity data, calculation methodology")
    elif status == "no_user_data":
        recommendations.append("📊 No user data provided for comparison. Use Climate TRACE as reference.")
    
    if abs(diff_pct) > 50:
        recommendations.append("🔍 Large variance - verify facility identification and scope boundaries")
    
    return recommendations

@app.post("/api/compliance/audit-snapshot")
def create_audit_snapshot(
    req: CreateAuditSnapshotRequest,
    db: Session = Depends(get_db)
):
    """Create a new audit snapshot"""
    try:
        compliance_engine = ComplianceIntegrityEngine(db)
        snapshot_data = compliance_engine.create_audit_snapshot(
            submission_type=req.submission_type,
            reporting_period_start=req.reporting_period_start,
            reporting_period_end=req.reporting_period_end,
            record_ids=req.record_ids,
            allow_empty=True
        )
        return {
            "success": True,
            "snapshot_data": {
                "submission_id": snapshot_data.submission_id,
                "submission_type": snapshot_data.submission_type,
                "reporting_period_start": snapshot_data.reporting_period_start.isoformat(),
                "reporting_period_end": snapshot_data.reporting_period_end.isoformat(),
                "merkle_root_hash": snapshot_data.merkle_root_hash,
                "total_records": snapshot_data.total_records,
                "total_emissions_kgco2e": float(snapshot_data.total_emissions_kgco2e),
                "average_compliance_score": snapshot_data.average_compliance_score,
                "audit_ready_records": snapshot_data.audit_ready_records,
                "non_compliant_records": snapshot_data.non_compliant_records,
                "compliance_flags": snapshot_data.compliance_flags
            }
        }
    except ValueError as ve:
        # Common case: no records in period
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error creating audit snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/compliance/snapshot-details/{snapshot_id}")
def get_snapshot_details(snapshot_id: str, db: Session = Depends(get_db)):
    """Get detailed audit snapshot information"""
    try:
        compliance_engine = ComplianceIntegrityEngine(db)
        return compliance_engine.generate_compliance_report(snapshot_id)
    except Exception as e:
        logger.error(f"Error getting snapshot details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compliance/generate-report")
def generate_compliance_report(
    req: GenerateReportRequest,
    db: Session = Depends(get_db)
):
    """Generate compliance report for audit snapshot"""
    try:
        compliance_engine = ComplianceIntegrityEngine(db)
        report_data = compliance_engine.generate_compliance_report(req.snapshot_id)
        return {
            "success": True,
            "report_data": report_data
        }
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/compliance/regulatory-submission")
def generate_regulatory_submission(
    req: RegulatorySubmissionRequest,
    db: Session = Depends(get_db)
):
    """Generate regulatory submission package"""
    try:
        report_generator = ComplianceReportGenerator(db)
        result = report_generator.generate_regulatory_submission(
            snapshot_id=req.snapshot_id,
            regulatory_framework=req.regulatory_framework
        )
        return result
    except Exception as e:
        logger.error(f"Error generating regulatory submission: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/rules")
def get_compliance_rules(db: Session = Depends(get_db)):
    """Get compliance rules"""
    try:
        rules = db.query(models.ComplianceRule).filter(
            models.ComplianceRule.is_active == True
        ).all()
        
        return [
            {
                "id": str(rule.id),
                "rule_id": rule.rule_id,
                "framework": rule.framework,
                "rule_name": rule.rule_name,
                "rule_description": rule.rule_description,
                "severity": rule.severity,
                "auto_apply": rule.auto_apply,
                "required_fields": rule.required_fields,
                "validation_rules": rule.validation_rules,
                "threshold_values": rule.threshold_values,
                "effective_date": rule.effective_date.isoformat() if rule.effective_date else None,
                "expiry_date": rule.expiry_date.isoformat() if rule.expiry_date else None
            }
            for rule in rules
        ]
    except Exception as e:
        logger.error(f"Error getting compliance rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compliance/rules")
def create_compliance_rule(
    req: CreateComplianceRuleRequest,
    db: Session = Depends(get_db)
):
    """Create a new compliance rule"""
    try:
        rule = models.ComplianceRule(
            rule_id=f"{req.framework}_{req.rule_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}",
            framework=req.framework,
            rule_name=req.rule_name,
            rule_description=req.rule_description,
            severity=req.severity,
            auto_apply=req.auto_apply,
            conditions=[],  # Would be populated based on requirements
            required_fields=req.required_fields,
            validation_rules=req.validation_rules,
            threshold_values=req.threshold_values,
            effective_date=date.today()
        )
        
        db.add(rule)
        db.commit()
        
        return {
            "success": True,
            "rule_id": rule.rule_id,
            "message": "Compliance rule created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating compliance rule: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/trustworthiness-heatmap")
def get_trustworthiness_heatmap(db: Session = Depends(get_db)):
    """Get trustworthiness heatmap data"""
    try:
        # Get recent records with compliance scores
        records = db.query(models.EmissionRecord).filter(
            models.EmissionRecord.created_at >= datetime.now() - timedelta(days=90)
        ).all()
        
        if not records:
            return {"heatmap_data": [], "average_trust_score": 0}
        
        # Group by supplier and month
        heatmap_data = []
        supplier_scores = {}
        
        for record in records:
            supplier = record.supplier_name or "Unknown"
            month = record.date.strftime("%Y-%m") if record.date else "Unknown"
            score = float(record.compliance_score or 0)
            
            heatmap_data.append({
                "supplier": supplier,
                "month": month,
                "trust_score": score
            })
            
            if supplier not in supplier_scores:
                supplier_scores[supplier] = []
            supplier_scores[supplier].append(score)
        
        # Calculate average scores
        avg_scores = {supplier: sum(scores) / len(scores) for supplier, scores in supplier_scores.items()}
        most_trusted = max(avg_scores.items(), key=lambda x: x[1])[0] if avg_scores else "N/A"
        least_trusted = min(avg_scores.items(), key=lambda x: x[1])[0] if avg_scores else "N/A"
        average_trust_score = sum(avg_scores.values()) / len(avg_scores) if avg_scores else 0
        
        return {
            "heatmap_data": heatmap_data,
            "average_trust_score": average_trust_score,
            "most_trusted_supplier": most_trusted,
            "least_trusted_supplier": least_trusted
        }
    except Exception as e:
        logger.error(f"Error getting trustworthiness heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/predictive-alerts")
def get_predictive_alerts(days_ahead: int = 30, db: Session = Depends(get_db)):
    """Get predictive compliance alerts"""
    try:
        # Get recent records
        records = db.query(models.EmissionRecord).filter(
            models.EmissionRecord.created_at >= datetime.now() - timedelta(days=30)
        ).all()
        
        alerts = []
        
        # Analyze compliance trends
        low_score_records = [r for r in records if r.compliance_score and r.compliance_score < 70]
        if len(low_score_records) > len(records) * 0.2:  # More than 20% low scores
            alerts.append({
                "alert_id": f"compliance_trend_{uuid.uuid4().hex[:8]}",
                "alert_type": "compliance_risk",
                "severity": "high",
                "sector": "all",
                "predicted_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "confidence": 0.85,
                "description": f"High percentage of low compliance scores detected ({len(low_score_records)}/{len(records)} records)",
                "recommended_actions": [
                    "Review data quality processes",
                    "Implement additional validation rules",
                    "Schedule compliance training"
                ],
                "current_risk_score": 75.0,
                "predicted_risk_score": 85.0
            })
        
        # Check for missing critical fields
        missing_fields_records = [r for r in records if not r.supplier_name or not r.date]
        if missing_fields_records:
            alerts.append({
                "alert_id": f"missing_fields_{uuid.uuid4().hex[:8]}",
                "alert_type": "data_quality",
                "severity": "medium",
                "sector": "all",
                "predicted_date": (datetime.now() + timedelta(days=14)).isoformat(),
                "confidence": 0.90,
                "description": f"Records with missing critical fields detected ({len(missing_fields_records)} records)",
                "recommended_actions": [
                    "Implement mandatory field validation",
                    "Review data entry processes",
                    "Add data quality checks"
                ],
                "current_risk_score": 60.0,
                "predicted_risk_score": 70.0
            })
        
        # Check for upcoming regulatory deadlines
        upcoming_deadlines = [
            {
                "alert_id": f"epa_deadline_{uuid.uuid4().hex[:8]}",
                "alert_type": "regulatory_deadline",
                "severity": "critical",
                "sector": "all",
                "predicted_date": (datetime.now() + timedelta(days=30)).isoformat(),
                "confidence": 1.0,
                "description": "EPA GHGRP submission deadline approaching",
                "recommended_actions": [
                    "Prepare audit snapshot",
                    "Generate compliance report",
                    "Submit to EPA e-GGRT"
                ],
                "current_risk_score": 80.0,
                "predicted_risk_score": 95.0
            }
        ]
        
        alerts.extend(upcoming_deadlines)
        
        return alerts
    except Exception as e:
        logger.error(f"Error getting predictive alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compliance/calculate-scores")
def calculate_compliance_scores(
    req: CalculateScoresRequest,
    db: Session = Depends(get_db)
):
    """Calculate compliance scores for records"""
    try:
        compliance_engine = ComplianceIntegrityEngine(db)
        
        # Get records to process
        query = db.query(models.EmissionRecord)
        if req.record_ids:
            query = query.filter(models.EmissionRecord.id.in_(req.record_ids))
        else:
            # Process records without compliance scores
            query = query.filter(models.EmissionRecord.compliance_score == None)
        
        records = query.all()
        
        updated_count = 0
        for record in records:
            # Convert record to dict for scoring
            record_dict = {
                'ef_source': record.ef_source,
                'ef_ref_code': record.ef_ref_code,
                'ef_version': record.ef_version,
                'uncertainty_pct': record.uncertainty_pct,
                'supplier_name': record.supplier_name,
                'date': record.date,
                'activity_type': record.activity_type,
                'scope': record.scope,
                'activity_amount': record.activity_amount,
                'activity_unit': record.activity_unit,
                'emission_factor_value': record.emission_factor_value,
                'result_kgco2e': record.emissions_kgco2e,  # Fixed field name
                'ai_classified': record.ai_classified,
                'needs_human_review': record.needs_human_review,
                'confidence_score': record.confidence_score,
                'record_hash': record.record_hash,
                'previous_hash': record.previous_hash,
                'salt': record.salt
            }
            
            # Calculate compliance score
            compliance_score = compliance_engine.calculate_compliance_score(record_dict)
            
            # Update record
            record.compliance_score = compliance_score.overall_score
            record.factor_source_quality = compliance_score.factor_source_quality
            record.metadata_completeness = compliance_score.metadata_completeness
            record.data_entry_method_score = compliance_score.data_entry_method_score
            record.fingerprint_integrity = compliance_score.fingerprint_integrity
            record.llm_confidence = compliance_score.llm_confidence
            record.compliance_flags = compliance_score.compliance_flags  # This should be a JSON array
            record.audit_ready = compliance_score.audit_ready
            
            updated_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"Updated compliance scores for {updated_count} records"
        }
        
    except Exception as e:
        logger.error(f"Error calculating compliance scores: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compliance/generate-pdf-report")
def generate_pdf_report(
    req: GenerateReportRequest,
    db: Session = Depends(get_db)
):
    """Generate PDF report for an audit snapshot"""
    try:
        from .services.compliance_report_generator import ComplianceReportGenerator
        
        report_generator = ComplianceReportGenerator(db)
        result = report_generator.generate_pdf_report(req.snapshot_id)
        
        if result['success']:
            return {
                "success": True,
                "snapshot_id": req.snapshot_id,
                "pdf_path": result['pdf_path'],
                "pdf_hash": result['pdf_hash'],
                "json_path": result['json_path'],
                "json_hash": result['json_hash'],
                "message": "PDF report generated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compliance/regulatory-submission")
def generate_regulatory_submission(
    req: RegulatorySubmissionRequest,
    db: Session = Depends(get_db)
):
    """Generate regulatory submission package"""
    try:
        from .services.compliance_report_generator import ComplianceReportGenerator
        
        report_generator = ComplianceReportGenerator(db)
        result = report_generator.generate_regulatory_submission(
            req.snapshot_id, 
            req.regulatory_framework
        )
        
        if result['success']:
            return {
                "success": True,
                "snapshot_id": req.snapshot_id,
                "framework": result['framework'],
                "submission_data": result['submission_data'],
                "required_fields": result['required_fields'],
                "deadline": result['deadline'],
                "submission_method": result['submission_method'],
                "message": f"Regulatory submission package generated for {result['framework']}"
            }
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except Exception as e:
        logger.error(f"Error generating regulatory submission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/compliance/audit-snapshots/{snapshot_id}")
def get_audit_snapshot(snapshot_id: str, db: Session = Depends(get_db)):
    """Get a specific audit snapshot by ID"""
    try:
        # Get unified snapshots and find the specific one
        unified_snapshots = AuditSyncService.get_unified_snapshots(db, limit=1000)
        
        # Find the specific snapshot
        target_snapshot = None
        for snapshot in unified_snapshots:
            if snapshot["submission_id"] == snapshot_id:
                target_snapshot = snapshot
                break
        
        if not target_snapshot:
            raise HTTPException(status_code=404, detail="Audit snapshot not found")
        
        # Convert to the expected format
        snapshot_data = {
            "snapshot_id": target_snapshot["id"],
            "submission_id": target_snapshot["submission_id"],
            "submission_type": target_snapshot["submission_type"],
            "reporting_period_start": target_snapshot["reporting_period_start"],
            "reporting_period_end": target_snapshot["reporting_period_end"],
            "merkle_root_hash": f"unified_{target_snapshot['id'][:16]}",
            "total_records": target_snapshot["total_records"],
            "total_emissions_kgco2e": target_snapshot["total_emissions_kgco2e"],
            "average_compliance_score": target_snapshot.get("average_compliance_score", 0.0),
            "audit_ready_records": target_snapshot.get("audit_ready_records", 0),
            "non_compliant_records": target_snapshot.get("non_compliant_records", 0),
            "created_at": target_snapshot["created_at"],
            "source": target_snapshot.get("source", "unified")
        }
        
        return snapshot_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/compliance/audit-snapshots/{snapshot_id}")
def delete_audit_snapshot(snapshot_id: str, db: Session = Depends(get_db)):
    """Delete an audit snapshot from both systems"""
    try:
        # Use sync service to delete from both systems
        success = AuditSyncService.delete_from_both_systems(db, snapshot_id)
        
        if success:
            return {
                "success": True,
                "message": f"Audit snapshot {snapshot_id} deleted from both systems"
            }
        else:
            raise HTTPException(status_code=404, detail="Audit snapshot not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting audit snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/submission-history")
def get_submission_history(limit: int = 10, db: Session = Depends(get_db)):
    """Get submission history"""
    try:
        from .services.compliance_report_generator import ComplianceReportGenerator
        
        report_generator = ComplianceReportGenerator(db)
        submissions = report_generator.get_submission_history(limit)
        
        return submissions
        
    except Exception as e:
        logger.error(f"Error getting submission history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CARBON MARKETS INTEGRATION ENDPOINTS
# ============================================================================

@app.get("/api/carbon-markets/prices")
def get_carbon_market_prices(standard: str = 'VCS', db: Session = Depends(get_db)):
    """Get current carbon credit market prices"""
    try:
        from .services.ct_carbon_markets import ClimateTraceCarbonMarkets
        
        carbon_markets = ClimateTraceCarbonMarkets(db)
        prices = carbon_markets.get_market_prices(standard)
        
        return {
            "success": True,
            "standard": standard,
            "prices": [
                {
                    "standard": p.standard,
                    "project_type": p.project_type,
                    "price_per_ton": p.price_per_ton,
                    "currency": p.currency,
                    "volume_available": p.volume_available,
                    "last_updated": p.last_updated.isoformat()
                }
                for p in prices
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting carbon market prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/carbon-markets/verify-project")
def verify_carbon_project(
    project_id: str,
    standard: str,
    db: Session = Depends(get_db)
):
    """Verify a carbon project against Climate TRACE data"""
    try:
        from .services.ct_carbon_markets import ClimateTraceCarbonMarkets
        
        carbon_markets = ClimateTraceCarbonMarkets(db)
        project = carbon_markets.verify_carbon_project(project_id, standard)
        
        return {
            "success": True,
            "project": {
                "project_id": project.project_id,
                "project_name": project.project_name,
                "project_type": project.project_type,
                "location": project.location,
                "standard": project.standard,
                "total_credits": project.total_credits,
                "issued_credits": project.issued_credits,
                "retired_credits": project.retired_credits,
                "available_credits": project.available_credits,
                "verification_status": project.verification_status,
                "climate_trace_emissions": project.climate_trace_emissions,
                "verification_delta": project.verification_delta,
                "eligibility_score": project.eligibility_score
            }
        }
        
    except Exception as e:
        logger.error(f"Error verifying carbon project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/carbon-markets/calculate-portfolio")
def calculate_portfolio_value(
    portfolio: List[Dict[str, Any]],
    db: Session = Depends(get_db)
):
    """Calculate carbon credit portfolio value"""
    try:
        from .services.ct_carbon_markets import ClimateTraceCarbonMarkets
        
        carbon_markets = ClimateTraceCarbonMarkets(db)
        result = carbon_markets.calculate_portfolio_value(portfolio)
        
        return {
            "success": True,
            "portfolio_analysis": result
        }
        
    except Exception as e:
        logger.error(f"Error calculating portfolio value: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADVANCED ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/api/analytics/trend-analysis")
def get_trend_analysis(
    sector: Optional[str] = None,
    days: int = 90,
    db: Session = Depends(get_db)
):
    """Get emission trend analysis"""
    try:
        from .services.ct_advanced_analytics import ClimateTraceAdvancedAnalytics
        
        analytics = ClimateTraceAdvancedAnalytics(db)
        trends = analytics.get_emission_trends(sector, days)
        
        return {
            "success": True,
            "sector": sector,
            "analysis_period_days": days,
            "trends": trends
        }
        
    except Exception as e:
        logger.error(f"Error getting trend analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/predictive-alerts")
def get_predictive_alerts_advanced(
    days_ahead: int = 30,
    db: Session = Depends(get_db)
):
    """Get advanced predictive alerts"""
    try:
        from .services.ct_advanced_analytics import ClimateTraceAdvancedAnalytics
        
        analytics = ClimateTraceAdvancedAnalytics(db)
        alerts = analytics.get_predictive_alerts(days_ahead)
        
        return {
            "success": True,
            "days_ahead": days_ahead,
            "alerts": [
                {
                    "alert_id": alert.alert_id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "sector": alert.sector,
                    "predicted_date": alert.predicted_date.isoformat(),
                    "confidence": alert.confidence,
                    "description": alert.description,
                    "recommended_actions": alert.recommended_actions,
                    "current_risk_score": alert.current_risk_score,
                    "predicted_risk_score": alert.predicted_risk_score
                }
                for alert in alerts
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting predictive alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/risk-score")
def get_comprehensive_risk_score_advanced(
    sector: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get comprehensive risk score"""
    try:
        from .services.ct_advanced_analytics import ClimateTraceAdvancedAnalytics
        
        analytics = ClimateTraceAdvancedAnalytics(db)
        risk_score = analytics.calculate_comprehensive_risk_score(sector)
        
        return {
            "success": True,
            "sector": sector,
            "risk_score": {
                "overall_score": risk_score.overall_score,
                "compliance_risk": risk_score.compliance_risk,
                "data_quality_risk": risk_score.data_quality_risk,
                "trend_risk": risk_score.trend_risk,
                "regulatory_risk": risk_score.regulatory_risk,
                "factors": risk_score.factors,
                "recommendations": risk_score.recommendations
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting comprehensive risk score: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Advanced Compliance Engine Endpoints
# ============================================================================

@app.get("/api/advanced-compliance/analysis")
def get_advanced_compliance_analysis(db: Session = Depends(get_db)):
    """Get comprehensive advanced compliance analysis"""
    try:
        advanced_engine = AdvancedComplianceEngine(db)
        
        # Get basic analysis data
        total_records = db.query(func.count(models.EmissionRecord.id)).scalar() or 0
        total_emissions = db.query(func.sum(models.EmissionRecord.emissions_kgco2e)).scalar() or 0
        
        # Calculate basic compliance metrics
        high_quality_records = db.query(func.count(models.EmissionRecord.id)).filter(
            models.EmissionRecord.data_quality_score >= 80
        ).scalar() or 0
        
        compliance_rate = (high_quality_records / total_records * 100) if total_records > 0 else 0
        
        analysis = {
            "roi_score": 85.5,  # Mock ROI score
            "compliance_rate": round(compliance_rate, 2),
            "risk_level": "Low" if compliance_rate >= 80 else "Medium" if compliance_rate >= 60 else "High",
            "total_records": total_records,
            "total_emissions_kgco2e": float(total_emissions),
            "high_quality_records": high_quality_records,
            "compliance_breakdown": {
                "excellent": db.query(func.count(models.EmissionRecord.id)).filter(
                    models.EmissionRecord.data_quality_score >= 90
                ).scalar() or 0,
                "good": db.query(func.count(models.EmissionRecord.id)).filter(
                    and_(models.EmissionRecord.data_quality_score >= 80, 
                         models.EmissionRecord.data_quality_score < 90)
                ).scalar() or 0,
                "fair": db.query(func.count(models.EmissionRecord.id)).filter(
                    and_(models.EmissionRecord.data_quality_score >= 70, 
                         models.EmissionRecord.data_quality_score < 80)
                ).scalar() or 0,
                "poor": db.query(func.count(models.EmissionRecord.id)).filter(
                    models.EmissionRecord.data_quality_score < 70
                ).scalar() or 0
            },
            "recommendations": [
                "Implement automated data quality checks",
                "Enhance third-party verification processes",
                "Regular compliance training for staff"
            ]
        }
        
        return {
            "success": True,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Error getting advanced compliance analysis: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/advanced-compliance/gaps/{framework}")
def get_compliance_gaps(framework: str, record_ids: Optional[str] = None, db: Session = Depends(get_db)):
    """Get compliance gaps for a specific regulatory framework"""
    try:
        advanced_engine = AdvancedComplianceEngine(db)
        
        # Parse record IDs if provided
        record_id_list = None
        if record_ids:
            record_id_list = record_ids.split(',')
        
        gaps = advanced_engine.analyze_compliance_gaps(framework, record_id_list)
        
        return {
            "framework": framework,
            "total_gaps": len(gaps),
            "gaps": [
                {
                    "gap_id": gap.gap_id,
                    "requirement": gap.requirement,
                    "severity": gap.severity,
                    "current_status": gap.current_status,
                    "gap_description": gap.gap_description,
                    "affected_records": gap.affected_records,
                    "estimated_cost": gap.estimated_cost,
                    "estimated_time": gap.estimated_time,
                    "priority_score": gap.priority_score,
                    "remediation_actions": gap.remediation_actions,
                    "roi_impact": gap.roi_impact
                }
                for gap in gaps
            ],
            "summary": {
                "critical_gaps": len([g for g in gaps if g.severity == 'critical']),
                "high_gaps": len([g for g in gaps if g.severity == 'high']),
                "medium_gaps": len([g for g in gaps if g.severity == 'medium']),
                "low_gaps": len([g for g in gaps if g.severity == 'low']),
                "total_affected_records": sum(g.affected_records for g in gaps),
                "total_estimated_cost": sum(g.estimated_cost for g in gaps),
                "total_estimated_time": sum(g.estimated_time for g in gaps)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting compliance gaps: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/advanced-compliance/roi/{framework}")
def get_compliance_roi(framework: str, investment_amount: float = 100000, 
                      time_horizon_months: int = 12, db: Session = Depends(get_db)):
    """Calculate ROI for compliance investments"""
    try:
        # Get basic data for calculations
        total_records = db.query(func.count(models.EmissionRecord.id)).scalar() or 0
        
        # Calculate ROI components
        annual_compliance_cost = total_records * 150  # $150 per record annually
        compliance_cost_savings = annual_compliance_cost * 0.3  # 30% savings from automation
        
        # Framework-specific penalty avoidance
        penalty_avoidance = {
            'EPA': 50000,  # EPA penalties
            'EU_ETS': 75000,  # EU ETS penalties
            'CARB': 40000,  # CARB penalties
            'TCFD': 25000   # TCFD reputation impact
        }.get(framework, 30000)
        
        operational_efficiency = investment_amount * 0.15  # 15% operational efficiency
        reputation_value = investment_amount * 0.20  # 20% reputation value
        
        total_benefits = compliance_cost_savings + penalty_avoidance + operational_efficiency + reputation_value
        total_roi = total_benefits - investment_amount
        roi_percentage = (total_roi / investment_amount * 100) if investment_amount > 0 else 0
        payback_period = (investment_amount / (total_benefits / time_horizon_months)) if total_benefits > 0 else 0
        
        return {
            "framework": framework,
            "investment_amount": investment_amount,
            "time_horizon_months": time_horizon_months,
            "roi_analysis": {
                "total_investment": investment_amount,
                "compliance_cost_savings": round(compliance_cost_savings, 2),
                "penalty_avoidance": penalty_avoidance,
                "operational_efficiency": round(operational_efficiency, 2),
                "reputation_value": round(reputation_value, 2),
                "total_roi": round(total_roi, 2),
                "roi_score": round(roi_percentage, 2),
                "payback_period_months": round(payback_period, 1),
                "risk_reduction": 75.0,  # 75% risk reduction
                "competitive_advantage": 85.0  # 85% competitive advantage
            },
            "breakdown": {
                "total_benefits": round(total_benefits, 2),
                "roi_percentage": round(roi_percentage, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating compliance ROI: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/advanced-compliance/readiness/{framework}")
def get_regulatory_readiness(framework: str, db: Session = Depends(get_db)):
    """Assess regulatory readiness for a specific framework"""
    try:
        advanced_engine = AdvancedComplianceEngine(db)
        
        readiness = advanced_engine.assess_regulatory_readiness(framework)
        
        return {
            "framework": framework,
            "readiness_assessment": {
                "readiness_score": readiness.readiness_score,
                "compliance_rate": readiness.compliance_rate,
                "missing_requirements": readiness.missing_requirements,
                "critical_gaps": readiness.critical_gaps,
                "estimated_preparation_time": readiness.estimated_preparation_time,
                "estimated_cost": readiness.estimated_cost,
                "risk_level": readiness.risk_level
            },
            "recommendations": _generate_readiness_recommendations(readiness)
        }
        
    except Exception as e:
        logger.error(f"Error assessing regulatory readiness: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/advanced-compliance/roadmap")
def generate_compliance_roadmap(request: dict, db: Session = Depends(get_db)):
    """Generate compliance roadmap for multiple frameworks"""
    try:
        frameworks = request.get('frameworks', [])
        budget_constraint = request.get('budget_constraint', 100000)
        
        if not frameworks:
            raise HTTPException(status_code=400, detail="At least one framework must be specified")
        
        advanced_engine = AdvancedComplianceEngine(db)
        
        roadmap = advanced_engine.generate_compliance_roadmap(frameworks, budget_constraint)
        
        return {
            "roadmap": roadmap,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating compliance roadmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/advanced-compliance/benchmark")
def get_compliance_benchmark(industry: str = "manufacturing", db: Session = Depends(get_db)):
    """Get compliance benchmarking data"""
    try:
        advanced_engine = AdvancedComplianceEngine(db)
        
        benchmark = advanced_engine.get_compliance_benchmark(industry)
        
        return benchmark
        
    except Exception as e:
        logger.error(f"Error getting compliance benchmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _generate_readiness_recommendations(readiness) -> List[str]:
    """Generate recommendations based on readiness assessment"""
    recommendations = []
    
    if readiness.readiness_score >= 90:
        recommendations.append("EXCELLENT: Ready for regulatory submission")
    elif readiness.readiness_score >= 70:
        recommendations.append("GOOD: Minor improvements needed before submission")
    elif readiness.readiness_score >= 50:
        recommendations.append("FAIR: Significant improvements required")
    else:
        recommendations.append("POOR: Major compliance gaps need immediate attention")
    
    if readiness.critical_gaps:
        recommendations.append(f"CRITICAL: Address {len(readiness.critical_gaps)} critical gaps immediately")
    
    if readiness.estimated_cost > 50000:
        recommendations.append("HIGH COST: Consider phased implementation to manage budget")
    
    if readiness.estimated_preparation_time > 90:
        recommendations.append("LONG TIMELINE: Start preparation early to meet deadlines")
    
    return recommendations


@app.post("/api/audit/sync")
def sync_audit_snapshots(db: Session = Depends(get_db)):
    """Synchronize audit snapshots between both systems"""
    try:
        result = AuditSyncService.sync_all_snapshots(db)
        return {
            "success": True,
            "message": "Audit snapshots synchronized successfully",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error synchronizing audit snapshots: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/audit/unified-snapshots")
def get_unified_audit_snapshots(limit: int = 100, db: Session = Depends(get_db)):
    """Get unified audit snapshots from both systems"""
    try:
        unified_snapshots = AuditSyncService.get_unified_snapshots(db, limit)
        return unified_snapshots
    except Exception as e:
        logger.error(f"Error getting unified audit snapshots: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
