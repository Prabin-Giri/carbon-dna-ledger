"""
Carbon DNA Ledger - FastAPI Backend
Main application entry point with all REST endpoints
"""
import os
from datetime import datetime, date
from typing import List, Optional
from uuid import UUID
import pandas as pd

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, extract

from . import models, schemas
from .db import get_db, engine
from .services import ingest, hashing, factors, scenario, analytics

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Carbon DNA Ledger", version="1.0.0")

# Enable CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Carbon DNA Ledger API", "version": "1.0.0"}

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
        "events with highest uncertainty": analytics.query_highest_uncertainty_template
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
