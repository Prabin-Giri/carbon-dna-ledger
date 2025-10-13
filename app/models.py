"""
SQLAlchemy models for Carbon DNA Ledger
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Text, SmallInteger, ForeignKey, Date, BigInteger, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .db import Base

class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    sector = Column(Text)
    region = Column(Text)
    data_quality_score = Column(Integer, default=50)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    events = relationship("CarbonEvent", back_populates="supplier")

class EmissionFactor(Base):
    __tablename__ = "emission_factors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(Text, nullable=False)
    description = Column(Text)
    scope = Column(SmallInteger, nullable=False)
    activity_category = Column(Text)
    region = Column(Text)
    value = Column(Numeric, nullable=False)
    unit = Column(Text, nullable=False)
    version = Column(Text)
    uncertainty_pct = Column(Numeric, default=0)
    factor_metadata = Column(JSON, default={})
    
    # Relationships
    events = relationship("CarbonEvent", back_populates="factor")

class CarbonEvent(Base):
    __tablename__ = "carbon_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    activity = Column(Text, nullable=False)
    scope = Column(SmallInteger, nullable=False)
    inputs = Column(JSON, nullable=False)
    factor_id = Column(UUID(as_uuid=True), ForeignKey("emission_factors.id"))
    method = Column(Text, nullable=False)
    result_kgco2e = Column(Numeric, nullable=False)
    uncertainty_pct = Column(Numeric, default=0)
    source_doc = Column(JSON, nullable=False)
    quality_flags = Column(JSON, default=[])
    fingerprint = Column(JSON, nullable=False)
    row_hash = Column(Text, nullable=False)
    prev_hash = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    supplier = relationship("Supplier", back_populates="events")
    factor = relationship("EmissionFactor", back_populates="events")

class MerkleRoot(Base):
    __tablename__ = "merkle_roots"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    period_date = Column(Date, nullable=False)
    root_hash = Column(Text, nullable=False)
    count_events = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EmissionRecord(Base):
    __tablename__ = "emission_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Common identifiers
    record_id = Column(Text)
    external_id = Column(Text)
    contract_id = Column(Text)
    instrument_type = Column(Text)
    supplier_name = Column(Text)

    # Organizational context
    org_unit = Column(Text)
    facility_id = Column(Text)
    country_code = Column(Text)

    # Time
    date_start = Column(Date)
    date_end = Column(Date)
    date = Column(Date)  # for simple CSV

    # Classification
    scope = Column(SmallInteger)
    category = Column(Text)
    subcategory = Column(Text)
    activity_type = Column(Text)

    # Activity details
    activity_amount = Column(Numeric)
    activity_unit = Column(Text)
    fuel_type = Column(Text)
    vehicle_type = Column(Text)
    distance_km = Column(Numeric)
    mass_tonnes = Column(Numeric)
    energy_kwh = Column(Numeric)
    grid_region = Column(Text)
    market_basis = Column(Text)
    renewable_percent = Column(Numeric)

    # Emission factor
    emission_factor_value = Column(Numeric)
    emission_factor_unit = Column(Text)
    ef_source = Column(Text)
    ef_ref_code = Column(Text)
    ef_version = Column(Text)
    gwp_set = Column(Text)

    # Results
    co2_kg = Column(Numeric)
    ch4_kg = Column(Numeric)
    n2o_kg = Column(Numeric)
    co2e_kg = Column(Numeric)

    # Methodology and quality
    methodology = Column(Text)
    data_quality_score = Column(Numeric)
    verification_status = Column(Text)
    uncertainty_pct = Column(Numeric, default=0)

    # Attachments / misc
    attachment_url = Column(Text)
    notes = Column(Text)

    # Simple CSV financial fields
    description = Column(Text)
    amount = Column(Numeric)
    currency = Column(Text)
    ef_factor_per_currency = Column(Numeric)
    emissions_kgco2e = Column(Numeric)
    project_code = Column(Text)

    # Calculation provenance
    calculation_method = Column(Text)
    calculation_metadata = Column(JSON, default={})

    # Hash chain
    previous_hash = Column(Text)
    record_hash = Column(Text)
    salt = Column(Text)

    # Raw row storage for completeness
    raw_row = Column(JSON, default={})
    
    # AI Classification fields
    ai_classified = Column(Boolean, default=False)  # true or false
    confidence_score = Column(Numeric, default=0.0)  # 0.0 to 1.0
    needs_human_review = Column(Boolean, default=False)
    ai_model_used = Column(Text)  # e.g., 'ollama:llama2', 'openai:gpt-4', 'local:bert'
    classification_metadata = Column(JSON, default={})  # Store AI reasoning, prompts, etc.
    
    # Climate TRACE taxonomy fields
    ct_sector = Column(Text)  # Climate TRACE sector (e.g., 'Power', 'Oil and Gas')
    ct_subsector = Column(Text)  # Climate TRACE subsector (e.g., 'Coal', 'Natural Gas')
    ct_asset_type = Column(Text)  # Climate TRACE asset type
    ct_asset_id = Column(Text)  # Climate TRACE asset identifier
    ct_country_code = Column(Text)  # ISO country code for CT mapping
    ct_region = Column(Text)  # Climate TRACE region
    
    # Compliance Integrity Engine fields
    compliance_score = Column(Numeric(5, 2), default=0.0)  # 0-100 compliance score
    factor_source_quality = Column(Numeric(5, 2), default=0.0)  # Quality of emission factor source
    metadata_completeness = Column(Numeric(5, 2), default=0.0)  # Completeness of metadata
    data_entry_method_score = Column(Numeric(5, 2), default=0.0)  # Score based on data entry method
    fingerprint_integrity = Column(Numeric(5, 2), default=0.0)  # Fingerprint integrity score
    llm_confidence = Column(Numeric(5, 2), default=0.0)  # LLM confidence if used
    compliance_flags = Column(JSON, default=[])  # Compliance issues and flags
    audit_ready = Column(Boolean, default=False)  # Whether record is audit-ready
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CarbonOpportunity(Base):
    """Carbon offset and credit opportunities detected from emission data"""
    __tablename__ = "carbon_opportunities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    emission_record_id = Column(UUID(as_uuid=True), ForeignKey("emission_records.id"))
    
    # Opportunity details
    opportunity_type = Column(Text, nullable=False)  # 'offset', 'tax_credit', 'grant'
    program_name = Column(Text, nullable=False)
    program_agency = Column(Text)
    description = Column(Text)
    
    # Value estimation
    potential_value = Column(Numeric(15, 2))
    confidence_score = Column(Numeric(3, 2))
    emissions_reduced = Column(Numeric(15, 6))
    
    # Application details
    application_link = Column(Text)
    deadline = Column(Date)
    requirements = Column(JSON)
    
    # Status tracking
    status = Column(Text, default='detected')  # 'detected', 'applied', 'approved', 'rejected'
    application_date = Column(DateTime(timezone=True))
    approval_date = Column(DateTime(timezone=True))
    actual_value = Column(Numeric(15, 2))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


## Duplicate definitions removed below (kept canonical versions later in file)


class ComplianceDeadline(Base):
    """Deadlines for carbon credit and grant applications"""
    __tablename__ = "compliance_deadlines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("carbon_opportunities.id"))
    
    # Deadline details
    program_name = Column(Text, nullable=False)
    deadline_type = Column(Text, nullable=False)  # 'application', 'submission', 'renewal'
    deadline_date = Column(Date, nullable=False)
    timezone = Column(Text, default='UTC')
    
    # Reminder settings
    reminder_days = Column(JSON)  # [30, 14, 7, 1] days before deadline
    last_reminder_sent = Column(DateTime(timezone=True))
    
    # Status
    is_active = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    completion_date = Column(DateTime(timezone=True))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


## Duplicate definitions removed above


class ApplicationTemplate(Base):
    """Pre-filled application templates for opportunities"""
    __tablename__ = "application_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_type = Column(Text, nullable=False)
    program_name = Column(Text, nullable=False)
    
    # Template details
    template_name = Column(Text, nullable=False)
    template_version = Column(Text, default='1.0')
    form_fields = Column(JSON)  # Pre-filled form data
    required_documents = Column(JSON)  # List of required documents
    
    # Application process
    application_url = Column(Text)
    submission_method = Column(Text)  # 'online', 'email', 'mail'
    processing_time = Column(Text)  # '30-60 days', etc.
    
    # Status
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ClimateTraceCrosscheck(Base):
    """Climate TRACE cross-check results for compliance verification"""
    __tablename__ = "ct_crosschecks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Time period
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    
    # Climate TRACE data
    ct_sector = Column(Text, nullable=False)
    ct_subsector = Column(Text)
    ct_country_code = Column(Text)
    ct_region = Column(Text)
    
    # Emissions comparison
    ct_emissions_kgco2e = Column(Numeric(20, 6))  # Climate TRACE reported emissions
    our_emissions_kgco2e = Column(Numeric(20, 6))  # Our ledger emissions
    delta_kgco2e = Column(Numeric(20, 6))  # Difference (our - CT)
    delta_percentage = Column(Numeric(8, 4))  # Percentage difference
    
    # Compliance status
    compliance_status = Column(Text, default='compliant')  # 'compliant', 'at_risk', 'non_compliant'
    threshold_exceeded = Column(Boolean, default=False)
    threshold_percentage = Column(Numeric(8, 4), default=10.0)  # Configurable threshold
    
    # Analysis metadata
    record_count = Column(Integer, default=0)  # Number of our records in this sector/month
    confidence_score = Column(Numeric(3, 2), default=0.0)  # 0.0-1.0
    data_quality_flags = Column(JSON, default=[])
    
    # Remediation suggestions
    remediation_suggestions = Column(JSON, default=[])
    suggested_actions = Column(Text)
    
    # Status tracking
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(Text)
    acknowledged_at = Column(DateTime(timezone=True))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AuditSnapshot(Base):
    """Audit snapshots for regulatory submissions and compliance verification"""
    __tablename__ = "audit_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Submission details
    submission_id = Column(Text, nullable=False, unique=True)
    submission_type = Column(Text, nullable=False)  # 'EPA', 'EU_ETS', 'CARB', 'TCFD', 'SEC'
    reporting_period_start = Column(Date, nullable=False)
    reporting_period_end = Column(Date, nullable=False)
    submission_date = Column(DateTime(timezone=True), nullable=False)
    
    # Cryptographic integrity
    merkle_root_hash = Column(Text, nullable=False)  # Root hash of all included records
    total_records = Column(Integer, nullable=False)  # Number of records in snapshot
    total_emissions_kgco2e = Column(Numeric(20, 6), nullable=False)  # Total emissions
    
    # Compliance metrics
    average_compliance_score = Column(Numeric(5, 2), default=0.0)
    audit_ready_records = Column(Integer, default=0)
    non_compliant_records = Column(Integer, default=0)
    compliance_flags = Column(JSON, default=[])
    
    # Generated reports
    pdf_report_path = Column(Text)  # Path to generated PDF report
    pdf_report_hash = Column(Text)  # Hash of PDF for integrity verification
    json_data_path = Column(Text)  # Path to JSON data export
    json_data_hash = Column(Text)  # Hash of JSON data
    
    # Regulatory submission
    regulatory_submission_id = Column(Text)  # External regulatory submission ID
    submission_status = Column(Text, default='draft')  # 'draft', 'submitted', 'approved', 'rejected'
    submission_confirmation = Column(Text)  # Regulatory confirmation number
    
    # Verification
    verified_by = Column(Text)  # Who verified the submission
    verification_date = Column(DateTime(timezone=True))
    verification_notes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ComplianceRule(Base):
    """Compliance rules for different regulatory frameworks"""
    __tablename__ = "compliance_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Rule identification
    rule_id = Column(Text, nullable=False, unique=True)
    framework = Column(Text, nullable=False)  # 'EPA', 'EU_ETS', 'CARB', 'TCFD', 'SEC'
    rule_name = Column(Text, nullable=False)
    rule_description = Column(Text)
    
    # Rule conditions
    conditions = Column(JSON, nullable=False)  # JSON conditions for rule matching
    severity = Column(Text, default='medium')  # 'low', 'medium', 'high', 'critical'
    auto_apply = Column(Boolean, default=True)  # Whether to auto-apply this rule
    
    # Compliance requirements
    required_fields = Column(JSON, default=[])  # Required fields for compliance
    validation_rules = Column(JSON, default=[])  # Validation rules
    threshold_values = Column(JSON, default={})  # Threshold values for compliance
    
    # Status
    is_active = Column(Boolean, default=True)
    effective_date = Column(Date)
    expiry_date = Column(Date)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
