"""
Pydantic schemas for request/response validation
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, validator

class IngestResponse(BaseModel):
    count_inserted: int
    sample_ids: List[str]

class CarbonEventSummary(BaseModel):
    id: UUID
    occurred_at: datetime
    supplier_name: str
    activity: str
    scope: int
    result_kgco2e: float
    uncertainty_pct: float
    quality_flags: List[str]

class CarbonEventDetail(BaseModel):
    id: UUID
    occurred_at: datetime
    supplier_name: str
    activity: str
    scope: int
    inputs: Dict[str, Any]
    method: str
    result_kgco2e: float
    uncertainty_pct: float
    source_doc: List[Dict[str, Any]]
    quality_flags: List[str]
    fingerprint: Dict[str, Any]
    factor_ref: str
    factor_value: float
    factor_unit: str
    prev_hash: Optional[str]
    row_hash: str
    created_at: datetime

class ScenarioChanges(BaseModel):
    fuel_type: Optional[str] = None
    distance_km: Optional[float] = None
    tonnage: Optional[float] = None
    kwh: Optional[float] = None
    grid_mix_renewables: Optional[float] = None
    factor_override_id: Optional[UUID] = None

class ScenarioResult(BaseModel):
    before: Dict[str, Any]
    after: Dict[str, Any]
    pct_change: float
    changed_tokens: List[str]

class QueryRequest(BaseModel):
    question: str
    params: Dict[str, Any] = {}

class QueryResult(BaseModel):
    template_name: str
    sql: str
    rows: List[Dict[str, Any]]

class MerkleRoot(BaseModel):
    id: int
    period_date: date
    root_hash: str
    count_events: int
    created_at: datetime

class TopEmitter(BaseModel):
    supplier_name: str
    total_kgco2e: float

class EmissionDelta(BaseModel):
    period: str
    total_kgco2e: float
    pct_change: Optional[float] = None

class QualityGap(BaseModel):
    id: UUID
    occurred_at: datetime
    supplier_name: str
    activity: str
    uncertainty_pct: float
    quality_flags: List[str]
    result_kgco2e: float

class IngestRecordsRequest(BaseModel):
    documentType: str
    headers: List[str]
    rows: List[Dict[str, Any]]

class IngestRecordsResponse(BaseModel):
    count_inserted: int
    errors: List[str] = []
