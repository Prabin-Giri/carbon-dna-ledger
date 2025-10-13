"""
Enhanced Audit Snapshot Models
Comprehensive audit trail system with immutable history and rich metadata
"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from enum import Enum

from sqlalchemy import (
    Column, String, Text, Integer, Numeric, DateTime, Date, Boolean, 
    ForeignKey, JSON, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import Base


class EmissionScope(str, Enum):
    """GHG Protocol emission scopes"""
    SCOPE_1 = "scope_1"  # Direct emissions
    SCOPE_2 = "scope_2"  # Indirect emissions from purchased energy
    SCOPE_3 = "scope_3"  # Other indirect emissions


class ActivityType(str, Enum):
    """Activity types for emissions categorization"""
    # Scope 1
    STATIONARY_COMBUSTION = "stationary_combustion"
    MOBILE_COMBUSTION = "mobile_combustion"
    PROCESS_EMISSIONS = "process_emissions"
    FUGITIVE_EMISSIONS = "fugitive_emissions"
    
    # Scope 2
    PURCHASED_ELECTRICITY = "purchased_electricity"
    PURCHASED_STEAM = "purchased_steam"
    PURCHASED_HEATING = "purchased_heating"
    PURCHASED_COOLING = "purchased_cooling"
    
    # Scope 3
    PURCHASED_GOODS = "purchased_goods"
    CAPITAL_GOODS = "capital_goods"
    FUEL_ENERGY_ACTIVITIES = "fuel_energy_activities"
    TRANSPORTATION = "transportation"
    WASTE_DISPOSAL = "waste_disposal"
    BUSINESS_TRAVEL = "business_travel"
    EMPLOYEE_COMMUTING = "employee_commuting"
    LEASED_ASSETS = "leased_assets"
    INVESTMENTS = "investments"


class DataSource(str, Enum):
    """Data source types for provenance tracking"""
    SENSOR = "sensor"
    MANUAL_INPUT = "manual_input"
    API_INTEGRATION = "api_integration"
    CALCULATED = "calculated"
    ESTIMATED = "estimated"
    THIRD_PARTY = "third_party"


class CalculationMethod(str, Enum):
    """Emission calculation methodologies"""
    ACTIVITY_BASED = "activity_based"
    SPEND_BASED = "spend_based"
    HYBRID = "hybrid"
    DIRECT_MEASUREMENT = "direct_measurement"


class ApprovalStatus(str, Enum):
    """Approval workflow status"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUBMITTED = "submitted"
    AUDITED = "audited"


class RegulatoryFramework(str, Enum):
    """Supported regulatory frameworks"""
    EPA = "epa"
    EU_ETS = "eu_ets"
    CARB = "carb"
    TCFD = "tcfd"
    SEC = "sec"
    CDP = "cdp"
    GRI = "gri"
    SASB = "sasb"
    CSRD = "csrd"


class EnhancedAuditSnapshotEntry(Base):
    """
    Individual audit snapshot entries with comprehensive metadata
    Each entry represents a single emission data point with full provenance
    """
    __tablename__ = "enhanced_audit_snapshot_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Parent snapshot reference
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey('enhanced_audit_snapshots.id'), nullable=False)
    
    # Timestamped record
    measurement_timestamp = Column(DateTime(timezone=True), nullable=False)
    created_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Scope and source categorization
    emission_scope = Column(SQLEnum(EmissionScope), nullable=False)
    activity_type = Column(SQLEnum(ActivityType), nullable=False)
    business_unit = Column(Text, nullable=True)
    facility_id = Column(Text, nullable=True)
    location = Column(Text, nullable=True)
    
    # Emission data
    activity_data = Column(Numeric(20, 6), nullable=False)  # Activity amount
    activity_unit = Column(Text, nullable=False)  # Unit of measurement
    emissions_kgco2e = Column(Numeric(20, 6), nullable=False)
    
    # Data provenance
    data_source = Column(SQLEnum(DataSource), nullable=False)
    source_system = Column(Text, nullable=True)  # System that provided the data
    source_user = Column(Text, nullable=True)  # User who input/verified the data
    source_document = Column(Text, nullable=True)  # Reference to source document
    
    # Emission factors and methodologies
    emission_factor = Column(Numeric(20, 6), nullable=False)
    emission_factor_source = Column(Text, nullable=False)  # EPA, GHG Protocol, etc.
    emission_factor_version = Column(Text, nullable=True)
    calculation_method = Column(SQLEnum(CalculationMethod), nullable=False)
    calculation_formula = Column(Text, nullable=True)  # Formula used
    
    # Quality and uncertainty
    uncertainty_percentage = Column(Numeric(5, 2), nullable=True)
    quality_score = Column(Numeric(5, 2), nullable=True)
    data_quality_flags = Column(JSON, default=[])
    
    # Approval workflow
    approval_status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.DRAFT)
    reviewed_by = Column(Text, nullable=True)
    review_timestamp = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    approved_by = Column(Text, nullable=True)
    approval_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Evidence and attachments
    evidence_files = Column(JSON, default=[])  # List of file references
    iot_device_ids = Column(JSON, default=[])  # IoT device references
    external_system_refs = Column(JSON, default=[])  # External system references
    
    # Metadata
    tags = Column(JSON, default=[])
    custom_attributes = Column(JSON, default={})
    notes = Column(Text, nullable=True)
    
    # Immutable audit trail
    created_by = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    snapshot = relationship("EnhancedAuditSnapshot", back_populates="entries")
    audit_logs = relationship("EnhancedAuditLogEntry", back_populates="snapshot_entry")
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_entries_snapshot_id', 'snapshot_id'),
        Index('idx_audit_entries_scope', 'emission_scope'),
        Index('idx_audit_entries_timestamp', 'measurement_timestamp'),
        Index('idx_audit_entries_status', 'approval_status'),
        Index('idx_audit_entries_business_unit', 'business_unit'),
    )


class EnhancedAuditSnapshot(Base):
    """
    Enhanced audit snapshots with comprehensive metadata and immutable history
    """
    __tablename__ = "enhanced_audit_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Submission details
    submission_id = Column(Text, nullable=False, unique=True)
    submission_type = Column(SQLEnum(RegulatoryFramework), nullable=False)
    reporting_period_start = Column(Date, nullable=False)
    reporting_period_end = Column(Date, nullable=False)
    submission_date = Column(DateTime(timezone=True), nullable=False)
    
    # Hierarchical organization
    organization_id = Column(Text, nullable=True)
    business_unit = Column(Text, nullable=True)
    reporting_entity = Column(Text, nullable=True)
    
    # Cryptographic integrity
    merkle_root_hash = Column(Text, nullable=False)
    total_records = Column(Integer, nullable=False)
    total_emissions_kgco2e = Column(Numeric(20, 6), nullable=False)
    
    # Scope breakdown
    scope_1_emissions = Column(Numeric(20, 6), default=0)
    scope_2_emissions = Column(Numeric(20, 6), default=0)
    scope_3_emissions = Column(Numeric(20, 6), default=0)
    
    # Compliance metrics
    average_compliance_score = Column(Numeric(5, 2), default=0.0)
    audit_ready_records = Column(Integer, default=0)
    non_compliant_records = Column(Integer, default=0)
    compliance_flags = Column(JSON, default=[])
    
    # Quality metrics
    average_uncertainty = Column(Numeric(5, 2), nullable=True)
    data_quality_score = Column(Numeric(5, 2), nullable=True)
    
    # Approval workflow
    approval_status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.DRAFT)
    workflow_stage = Column(Text, default='data_collection')  # data_collection, review, approval, submission
    
    # Multi-level sign-offs
    data_collector = Column(Text, nullable=True)
    data_collector_timestamp = Column(DateTime(timezone=True), nullable=True)
    reviewer = Column(Text, nullable=True)
    reviewer_timestamp = Column(DateTime(timezone=True), nullable=True)
    approver = Column(Text, nullable=True)
    approver_timestamp = Column(DateTime(timezone=True), nullable=True)
    auditor = Column(Text, nullable=True)
    auditor_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Regulatory submission
    regulatory_submission_id = Column(Text, nullable=True)
    submission_status = Column(Text, default='draft')
    submission_confirmation = Column(Text, nullable=True)
    regulatory_deadline = Column(Date, nullable=True)
    
    # Generated reports and exports
    pdf_report_path = Column(Text, nullable=True)
    pdf_report_hash = Column(Text, nullable=True)
    json_data_path = Column(Text, nullable=True)
    json_data_hash = Column(Text, nullable=True)
    excel_export_path = Column(Text, nullable=True)
    excel_export_hash = Column(Text, nullable=True)
    
    # Regulatory framework specific data
    framework_specific_data = Column(JSON, default={})
    
    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=[])
    custom_attributes = Column(JSON, default={})
    
    # Immutable audit trail
    created_by = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    entries = relationship("EnhancedAuditSnapshotEntry", back_populates="snapshot", cascade="all, delete-orphan")
    audit_logs = relationship("EnhancedAuditLogEntry", back_populates="snapshot")
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_snapshots_submission_id', 'submission_id'),
        Index('idx_audit_snapshots_type', 'submission_type'),
        Index('idx_audit_snapshots_period', 'reporting_period_start', 'reporting_period_end'),
        Index('idx_audit_snapshots_status', 'approval_status'),
        Index('idx_audit_snapshots_created_at', 'created_at'),
        Index('idx_audit_snapshots_organization', 'organization_id'),
    )


class EnhancedAuditLogEntry(Base):
    """
    Immutable audit log for all changes and actions
    Event-sourced architecture for complete audit trail
    """
    __tablename__ = "enhanced_audit_log_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey('enhanced_audit_snapshots.id'), nullable=True)
    snapshot_entry_id = Column(UUID(as_uuid=True), ForeignKey('enhanced_audit_snapshot_entries.id'), nullable=True)
    
    # Event details
    event_type = Column(Text, nullable=False)  # CREATE, UPDATE, DELETE, APPROVE, REJECT, etc.
    event_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    event_description = Column(Text, nullable=False)
    
    # Actor information
    actor_id = Column(Text, nullable=False)  # User ID or system ID
    actor_type = Column(Text, nullable=False)  # USER, SYSTEM, API, etc.
    actor_role = Column(Text, nullable=True)  # DATA_COLLECTOR, REVIEWER, APPROVER, etc.
    
    # Change details
    old_values = Column(JSON, nullable=True)  # Previous state
    new_values = Column(JSON, nullable=True)  # New state
    changed_fields = Column(JSON, nullable=True)  # List of changed fields
    
    # Context
    ip_address = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)
    session_id = Column(Text, nullable=True)
    
    # Additional metadata
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=[])
    
    # Relationships
    snapshot = relationship("EnhancedAuditSnapshot", back_populates="audit_logs")
    snapshot_entry = relationship("EnhancedAuditSnapshotEntry", back_populates="audit_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_logs_snapshot_id', 'snapshot_id'),
        Index('idx_audit_logs_entry_id', 'snapshot_entry_id'),
        Index('idx_audit_logs_event_type', 'event_type'),
        Index('idx_audit_logs_timestamp', 'event_timestamp'),
        Index('idx_audit_logs_actor', 'actor_id'),
    )


class EmissionFactorRegistry(Base):
    """
    Registry of emission factors with versioning and source tracking
    """
    __tablename__ = "emission_factor_registry"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Factor identification
    factor_name = Column(Text, nullable=False)
    factor_code = Column(Text, nullable=False)
    version = Column(Text, nullable=False)
    
    # Factor details
    emission_factor = Column(Numeric(20, 6), nullable=False)
    unit = Column(Text, nullable=False)
    co2_factor = Column(Numeric(20, 6), nullable=False)
    ch4_factor = Column(Numeric(20, 6), default=0)
    n2o_factor = Column(Numeric(20, 6), default=0)
    
    # Source information
    source_organization = Column(Text, nullable=False)  # EPA, GHG Protocol, etc.
    source_document = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
    publication_date = Column(Date, nullable=True)
    
    # Applicability
    emission_scope = Column(SQLEnum(EmissionScope), nullable=False)
    activity_type = Column(SQLEnum(ActivityType), nullable=False)
    applicable_regions = Column(JSON, default=[])
    applicable_industries = Column(JSON, default=[])
    
    # Quality and uncertainty
    uncertainty_percentage = Column(Numeric(5, 2), nullable=True)
    quality_rating = Column(Text, nullable=True)  # HIGH, MEDIUM, LOW
    
    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Metadata
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Audit trail
    created_by = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_emission_factors_code', 'factor_code'),
        Index('idx_emission_factors_scope', 'emission_scope'),
        Index('idx_emission_factors_activity', 'activity_type'),
        Index('idx_emission_factors_source', 'source_organization'),
        UniqueConstraint('factor_code', 'version', name='uq_factor_code_version'),
    )


class EvidenceFile(Base):
    """
    Evidence files and attachments for audit snapshots
    """
    __tablename__ = "evidence_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # File details
    filename = Column(Text, nullable=False)
    original_filename = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(Text, nullable=False)
    file_hash = Column(Text, nullable=False)  # SHA-256 hash for integrity
    
    # References
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey('enhanced_audit_snapshots.id'), nullable=True)
    snapshot_entry_id = Column(UUID(as_uuid=True), ForeignKey('enhanced_audit_snapshot_entries.id'), nullable=True)
    
    # File metadata
    upload_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_by = Column(Text, nullable=False)
    file_description = Column(Text, nullable=True)
    file_category = Column(Text, nullable=True)  # INVOICE, RECEIPT, CERTIFICATE, etc.
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    processing_notes = Column(Text, nullable=True)
    
    # Access control
    is_public = Column(Boolean, default=False)
    access_level = Column(Text, default='restricted')  # PUBLIC, RESTRICTED, CONFIDENTIAL
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_evidence_files_snapshot_id', 'snapshot_id'),
        Index('idx_evidence_files_entry_id', 'snapshot_entry_id'),
        Index('idx_evidence_files_hash', 'file_hash'),
        Index('idx_evidence_files_uploaded_by', 'uploaded_by'),
    )
