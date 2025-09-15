"""
SQLAlchemy models for Carbon DNA Ledger
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Text, SmallInteger, ForeignKey, Date, BigInteger, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    metadata = Column(JSONB, default={})
    
    # Relationships
    events = relationship("CarbonEvent", back_populates="factor")

class CarbonEvent(Base):
    __tablename__ = "carbon_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    activity = Column(Text, nullable=False)
    scope = Column(SmallInteger, nullable=False)
    inputs = Column(JSONB, nullable=False)
    factor_id = Column(UUID(as_uuid=True), ForeignKey("emission_factors.id"))
    method = Column(Text, nullable=False)
    result_kgco2e = Column(Numeric, nullable=False)
    uncertainty_pct = Column(Numeric, default=0)
    source_doc = Column(JSONB, nullable=False)
    quality_flags = Column(ARRAY(Text))
    fingerprint = Column(JSONB, nullable=False)
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
