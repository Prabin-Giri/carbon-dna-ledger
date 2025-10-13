"""
Enhanced Audit Snapshot Service
Comprehensive audit trail system with immutable history and rich metadata
"""
import uuid
import hashlib
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
from sqlalchemy.exc import IntegrityError

from ..models import EmissionRecord
from ..models_enhanced_audit import (
    EnhancedAuditSnapshot, EnhancedAuditSnapshotEntry, EnhancedAuditLogEntry, 
    EmissionFactorRegistry, EvidenceFile,
    EmissionScope, ActivityType, DataSource, CalculationMethod,
    ApprovalStatus, RegulatoryFramework
)
import logging

logger = logging.getLogger(__name__)


@dataclass
class EnhancedAuditSnapshotRequest:
    """Request structure for creating audit snapshots"""
    submission_type: RegulatoryFramework
    reporting_period_start: date
    reporting_period_end: date
    organization_id: Optional[str] = None
    business_unit: Optional[str] = None
    reporting_entity: Optional[str] = None
    description: Optional[str] = None
    record_ids: Optional[List[str]] = None
    include_scope_1: bool = True
    include_scope_2: bool = True
    include_scope_3: bool = True
    created_by: str = "system"


@dataclass
class EnhancedAuditSnapshotResponse:
    """Response structure for audit snapshot operations"""
    success: bool
    snapshot_id: str
    submission_id: str
    total_records: int
    total_emissions_kgco2e: Decimal
    scope_breakdown: Dict[str, Decimal]
    compliance_metrics: Dict[str, Any]
    approval_status: ApprovalStatus
    message: str
    errors: List[str] = None


class EnhancedAuditSnapshotService:
    """
    Enhanced audit snapshot service with comprehensive audit trail capabilities
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_audit_snapshot(self, request: EnhancedAuditSnapshotRequest) -> EnhancedAuditSnapshotResponse:
        """
        Create a comprehensive audit snapshot with full provenance tracking
        
        Args:
            request: EnhancedAuditSnapshotRequest with all required parameters
            
        Returns:
            EnhancedAuditSnapshotResponse with detailed results
        """
        try:
            # Generate unique submission ID
            submission_id = self._generate_submission_id(
                request.submission_type, 
                request.reporting_period_start, 
                request.reporting_period_end
            )
            
            # Get emission records for the period
            records = self._get_emission_records(
                request.reporting_period_start,
                request.reporting_period_end,
                request.record_ids,
                request.include_scope_1,
                request.include_scope_2,
                request.include_scope_3
            )
            
            if not records:
                return EnhancedAuditSnapshotResponse(
                    success=False,
                    snapshot_id="",
                    submission_id=submission_id,
                    total_records=0,
                    total_emissions_kgco2e=Decimal('0'),
                    scope_breakdown={},
                    compliance_metrics={},
                    approval_status=ApprovalStatus.DRAFT,
                    message="No emission records found for the specified period",
                    errors=["No records found"]
                )
            
            # Create audit snapshot
            snapshot = EnhancedAuditSnapshot(
                submission_id=submission_id,
                submission_type=request.submission_type,
                reporting_period_start=request.reporting_period_start,
                reporting_period_end=request.reporting_period_end,
                submission_date=datetime.now(),
                organization_id=request.organization_id,
                business_unit=request.business_unit,
                reporting_entity=request.reporting_entity,
                description=request.description,
                created_by=request.created_by,
                merkle_root_hash="pending",  # Will be updated after processing records
                total_records=0,  # Will be updated after processing records
                total_emissions_kgco2e=Decimal('0')  # Will be updated after processing records
            )
            
            # Save snapshot to database first to get the ID
            self.db.add(snapshot)
            self.db.commit()
            self.db.refresh(snapshot)  # Refresh to get the ID
            
            # Process records and create entries
            total_emissions = Decimal('0')
            scope_breakdown = {
                'scope_1': Decimal('0'),
                'scope_2': Decimal('0'),
                'scope_3': Decimal('0')
            }
            compliance_scores = []
            audit_ready_count = 0
            non_compliant_count = 0
            
            for record in records:
                # Create audit snapshot entry
                entry = self._create_snapshot_entry(record, snapshot.id)
                
                # Calculate totals
                emissions = Decimal(str(record.emissions_kgco2e or 0))
                total_emissions += emissions
                
                # Scope breakdown
                scope = self._determine_emission_scope(record)
                if scope == EmissionScope.SCOPE_1:
                    scope_breakdown['scope_1'] += emissions
                elif scope == EmissionScope.SCOPE_2:
                    scope_breakdown['scope_2'] += emissions
                elif scope == EmissionScope.SCOPE_3:
                    scope_breakdown['scope_3'] += emissions
                
                # Calculate compliance metrics using the compliance integrity engine
                # Create engine once outside the loop for efficiency
                if not hasattr(self, '_compliance_engine'):
                    from .compliance_integrity_engine import ComplianceIntegrityEngine
                    self._compliance_engine = ComplianceIntegrityEngine(self.db)
                
                # Convert record to dict for compliance scoring
                record_dict = {
                    'id': record.id,
                    'date': record.date.isoformat() if record.date else None,
                    'supplier_name': record.supplier_name,
                    'activity_type': record.activity_type,
                    'scope': record.scope,
                    'emissions_kgco2e': float(record.emissions_kgco2e or 0),
                    'data_quality_score': float(record.data_quality_score or 0),
                    'methodology': record.methodology,
                    'category': record.category,
                    'activity_amount': float(record.activity_amount or 0),
                    'activity_unit': record.activity_unit,
                    'created_at': record.created_at.isoformat() if record.created_at else None
                }
                
                # Calculate compliance score
                compliance_score = self._compliance_engine.calculate_compliance_score(record_dict)
                compliance_scores.append(compliance_score.overall_score)
                
                if compliance_score.audit_ready:
                    audit_ready_count += 1
                if compliance_score.overall_score < 70:
                    non_compliant_count += 1
                
                self.db.add(entry)
            
            # Calculate final metrics
            average_compliance_score = (
                sum(compliance_scores) / len(compliance_scores) 
                if compliance_scores else 0
            )
            
            # Generate Merkle root hash
            merkle_root_hash = self._generate_merkle_root(records)
            
            # Update snapshot with calculated values
            snapshot.total_records = len(records)
            snapshot.total_emissions_kgco2e = total_emissions
            snapshot.scope_1_emissions = scope_breakdown['scope_1']
            snapshot.scope_2_emissions = scope_breakdown['scope_2']
            snapshot.scope_3_emissions = scope_breakdown['scope_3']
            snapshot.average_compliance_score = Decimal(str(average_compliance_score))
            snapshot.audit_ready_records = audit_ready_count
            snapshot.non_compliant_records = non_compliant_count
            snapshot.merkle_root_hash = merkle_root_hash
            
            # Update the snapshot with calculated values
            self.db.commit()
            
            # Create audit log entry
            self._create_audit_log(
                snapshot_id=snapshot.id,
                event_type="CREATE",
                event_description=f"Created audit snapshot {submission_id}",
                actor_id=request.created_by,
                actor_type="USER",
                new_values={
                    "submission_id": submission_id,
                    "total_records": len(records),
                    "total_emissions": float(total_emissions)
                }
            )
            
            return EnhancedAuditSnapshotResponse(
                success=True,
                snapshot_id=str(snapshot.id),
                submission_id=submission_id,
                total_records=len(records),
                total_emissions_kgco2e=total_emissions,
                scope_breakdown=scope_breakdown,
                compliance_metrics={
                    "average_compliance_score": average_compliance_score,
                    "audit_ready_records": audit_ready_count,
                    "non_compliant_records": non_compliant_count,
                    "compliance_rate": (audit_ready_count / len(records) * 100) if records else 0
                },
                approval_status=ApprovalStatus.DRAFT,
                message="Audit snapshot created successfully"
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating audit snapshot: {e}")
            return EnhancedAuditSnapshotResponse(
                success=False,
                snapshot_id="",
                submission_id=submission_id if 'submission_id' in locals() else "",
                total_records=0,
                total_emissions_kgco2e=Decimal('0'),
                scope_breakdown={},
                compliance_metrics={},
                approval_status=ApprovalStatus.DRAFT,
                message=f"Error creating audit snapshot: {str(e)}",
                errors=[str(e)]
            )
    
    def _create_snapshot_entry(self, record: EmissionRecord, snapshot_id: uuid.UUID) -> EnhancedAuditSnapshotEntry:
        """Create a detailed audit snapshot entry from an emission record"""
        
        # Determine scope and activity type
        scope = self._determine_emission_scope(record)
        activity_type = self._determine_activity_type(record)
        
        # Determine data source
        data_source = self._determine_data_source(record)
        
        # Get emission factor information
        emission_factor, factor_source = self._get_emission_factor_info(record)
        
        # Determine calculation method
        calculation_method = self._determine_calculation_method(record)
        
        entry = EnhancedAuditSnapshotEntry(
            snapshot_id=snapshot_id,
            measurement_timestamp=record.date,
            emission_scope=scope,
            activity_type=activity_type,
            business_unit=getattr(record, 'business_unit', None),
            facility_id=getattr(record, 'facility_id', None),
            location=getattr(record, 'location', None),
            activity_data=Decimal(str(getattr(record, 'activity_amount', 0) or 0)),
            activity_unit=getattr(record, 'activity_unit', 'unknown') or 'unknown',
            emissions_kgco2e=Decimal(str(record.emissions_kgco2e or 0)),
            data_source=data_source,
            source_system=getattr(record, 'source_system', None),
            source_user=getattr(record, 'created_by', None),
            source_document=getattr(record, 'source_document', None),
            emission_factor=emission_factor,
            emission_factor_source=factor_source,
            calculation_method=calculation_method,
            calculation_formula=self._get_calculation_formula(record),
            uncertainty_percentage=getattr(record, 'uncertainty_percentage', None),
            quality_score=getattr(record, 'data_quality_score', None),
            data_quality_flags=getattr(record, 'data_quality_flags', []) or [],
            approval_status=ApprovalStatus.DRAFT,
            evidence_files=getattr(record, 'evidence_files', []) or [],
            iot_device_ids=getattr(record, 'iot_device_ids', []) or [],
            external_system_refs=getattr(record, 'external_system_refs', []) or [],
            tags=getattr(record, 'tags', []) or [],
            custom_attributes=getattr(record, 'custom_attributes', {}) or {},
            notes=getattr(record, 'notes', None),
            created_by=getattr(record, 'created_by', 'system')
        )
        
        return entry
    
    def _determine_emission_scope(self, record: EmissionRecord) -> EmissionScope:
        """Determine emission scope based on record data"""
        # This is a simplified mapping - in practice, this would be more sophisticated
        if hasattr(record, 'emission_scope') and record.emission_scope:
            return EmissionScope(record.emission_scope)
        
        # Default mapping based on activity type or other indicators
        activity_type = (getattr(record, 'activity_type', '') or '').lower()
        if any(keyword in activity_type for keyword in ['combustion', 'process', 'fugitive']):
            return EmissionScope.SCOPE_1
        elif any(keyword in activity_type for keyword in ['electricity', 'steam', 'heating', 'cooling']):
            return EmissionScope.SCOPE_2
        else:
            return EmissionScope.SCOPE_3
    
    def _determine_activity_type(self, record: EmissionRecord) -> ActivityType:
        """Determine activity type based on record data"""
        if hasattr(record, 'activity_type') and record.activity_type:
            try:
                return ActivityType(record.activity_type)
            except ValueError:
                pass
        
        # Default mapping
        activity_type = (getattr(record, 'activity_type', '') or '').lower()
        if 'combustion' in activity_type:
            return ActivityType.STATIONARY_COMBUSTION
        elif 'electricity' in activity_type:
            return ActivityType.PURCHASED_ELECTRICITY
        elif 'transport' in activity_type:
            return ActivityType.TRANSPORTATION
        else:
            return ActivityType.PURCHASED_GOODS
    
    def _determine_data_source(self, record: EmissionRecord) -> DataSource:
        """Determine data source based on record metadata"""
        if hasattr(record, 'data_source') and record.data_source:
            try:
                return DataSource(record.data_source)
            except ValueError:
                pass
        
        # Default mapping
        if getattr(record, 'is_sensor_data', False):
            return DataSource.SENSOR
        elif getattr(record, 'is_api_data', False):
            return DataSource.API_INTEGRATION
        elif getattr(record, 'is_calculated', False):
            return DataSource.CALCULATED
        else:
            return DataSource.MANUAL_INPUT
    
    def _determine_calculation_method(self, record: EmissionRecord) -> CalculationMethod:
        """Determine calculation method based on record data"""
        if hasattr(record, 'calculation_method') and record.calculation_method:
            try:
                return CalculationMethod(record.calculation_method)
            except ValueError:
                pass
        
        # Default mapping
        if getattr(record, 'is_activity_based', True):
            return CalculationMethod.ACTIVITY_BASED
        else:
            return CalculationMethod.SPEND_BASED
    
    def _get_emission_factor_info(self, record: EmissionRecord) -> Tuple[Decimal, str]:
        """Get emission factor and source information"""
        # Calculate emission factor from available data
        if record.activity_amount and record.emissions_kgco2e:
            emission_factor = Decimal(str(record.emissions_kgco2e / record.activity_amount))
        else:
            emission_factor = Decimal('0')
        
        # Use methodology as factor source
        factor_source = getattr(record, 'methodology', 'Unknown')
        return emission_factor, factor_source
    
    def _get_calculation_formula(self, record: EmissionRecord) -> str:
        """Get calculation formula used"""
        return getattr(record, 'calculation_formula', 'Activity Data × Emission Factor')
    
    def _get_emission_records(
        self, 
        start_date: date, 
        end_date: date, 
        record_ids: Optional[List[str]] = None,
        include_scope_1: bool = True,
        include_scope_2: bool = True,
        include_scope_3: bool = True
    ) -> List[EmissionRecord]:
        """Get emission records for the specified period and scope"""
        
        query = self.db.query(EmissionRecord).filter(
            and_(
                EmissionRecord.date >= start_date,
                EmissionRecord.date <= end_date
            )
        )
        
        if record_ids:
            query = query.filter(EmissionRecord.id.in_(record_ids))
        
        # Apply scope filters if needed
        # Note: This is simplified - in practice, you'd have scope fields in EmissionRecord
        # or use the enhanced models with proper scope categorization
        
        return query.all()
    
    def _generate_submission_id(
        self, 
        submission_type: RegulatoryFramework, 
        start_date: date, 
        end_date: date
    ) -> str:
        """Generate unique submission ID"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        random_suffix = uuid.uuid4().hex[:8]
        return f"{submission_type.value}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{timestamp}_{random_suffix}"
    
    def _generate_merkle_root(self, records: List[EmissionRecord]) -> str:
        """Generate Merkle root hash for cryptographic integrity"""
        if not records:
            return ""
        
        # Create leaf hashes for each record
        leaf_hashes = []
        for record in records:
            activity_data = getattr(record, 'activity_amount', 0) or 0
            record_data = f"{record.id}_{record.date}_{record.emissions_kgco2e}_{activity_data}"
            leaf_hash = hashlib.sha256(record_data.encode()).hexdigest()
            leaf_hashes.append(leaf_hash)
        
        # Build Merkle tree
        while len(leaf_hashes) > 1:
            next_level = []
            for i in range(0, len(leaf_hashes), 2):
                left = leaf_hashes[i]
                right = leaf_hashes[i + 1] if i + 1 < len(leaf_hashes) else left
                combined = hashlib.sha256((left + right).encode()).hexdigest()
                next_level.append(combined)
            leaf_hashes = next_level
        
        return leaf_hashes[0] if leaf_hashes else ""
    
    def _create_audit_log(
        self,
        snapshot_id: uuid.UUID,
        event_type: str,
        event_description: str,
        actor_id: str,
        actor_type: str = "USER",
        actor_role: Optional[str] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        notes: Optional[str] = None
    ):
        """Create immutable audit log entry"""
        
        log_entry = EnhancedAuditLogEntry(
            snapshot_id=snapshot_id,
            event_type=event_type,
            event_description=event_description,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_role=actor_role,
            old_values=old_values,
            new_values=new_values,
            notes=notes
        )
        
        self.db.add(log_entry)
        self.db.commit()
    
    def update_approval_status(
        self, 
        snapshot_id: str, 
        new_status: ApprovalStatus, 
        actor_id: str,
        actor_role: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update approval status with audit trail"""
        try:
            snapshot = self.db.query(EnhancedAuditSnapshot).filter(
                EnhancedAuditSnapshot.submission_id == snapshot_id
            ).first()
            
            if not snapshot:
                return False
            
            old_status = snapshot.approval_status
            snapshot.approval_status = new_status
            
            # Update role-specific timestamps
            now = datetime.now()
            if actor_role == "REVIEWER":
                snapshot.reviewer = actor_id
                snapshot.reviewer_timestamp = now
            elif actor_role == "APPROVER":
                snapshot.approver = actor_id
                snapshot.approver_timestamp = now
            elif actor_role == "AUDITOR":
                snapshot.auditor = actor_id
                snapshot.auditor_timestamp = now
            
            self.db.commit()
            
            # Create audit log
            self._create_audit_log(
                snapshot_id=snapshot.id,
                event_type="STATUS_UPDATE",
                event_description=f"Approval status changed from {old_status} to {new_status}",
                actor_id=actor_id,
                actor_type="USER",
                actor_role=actor_role,
                old_values={"approval_status": old_status.value},
                new_values={"approval_status": new_status.value},
                notes=notes
            )
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating approval status: {e}")
            return False
    
    def get_audit_snapshot_details(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed audit snapshot information"""
        try:
            snapshot = self.db.query(EnhancedAuditSnapshot).filter(
                EnhancedAuditSnapshot.submission_id == snapshot_id
            ).first()
            
            if not snapshot:
                return None
            
            # Get entries
            entries = self.db.query(EnhancedAuditSnapshotEntry).filter(
                EnhancedAuditSnapshotEntry.snapshot_id == snapshot.id
            ).all()
            
            # Get audit logs
            audit_logs = self.db.query(EnhancedAuditLogEntry).filter(
                EnhancedAuditLogEntry.snapshot_id == snapshot.id
            ).order_by(desc(EnhancedAuditLogEntry.event_timestamp)).all()
            
            return {
                "snapshot": {
                    "id": str(snapshot.id),
                    "submission_id": snapshot.submission_id,
                    "submission_type": snapshot.submission_type.value,
                    "reporting_period_start": snapshot.reporting_period_start.isoformat(),
                    "reporting_period_end": snapshot.reporting_period_end.isoformat(),
                    "total_records": snapshot.total_records,
                    "total_emissions_kgco2e": float(snapshot.total_emissions_kgco2e),
                    "scope_breakdown": {
                        "scope_1": float(snapshot.scope_1_emissions),
                        "scope_2": float(snapshot.scope_2_emissions),
                        "scope_3": float(snapshot.scope_3_emissions)
                    },
                    "compliance_metrics": {
                        "average_compliance_score": float(snapshot.average_compliance_score),
                        "audit_ready_records": snapshot.audit_ready_records,
                        "non_compliant_records": snapshot.non_compliant_records
                    },
                    "approval_status": snapshot.approval_status.value,
                    "workflow_stage": snapshot.workflow_stage,
                    "created_at": snapshot.created_at.isoformat(),
                    "created_by": snapshot.created_by
                },
                "entries": [
                    {
                        "id": str(entry.id),
                        "measurement_timestamp": entry.measurement_timestamp.isoformat(),
                        "emission_scope": entry.emission_scope.value,
                        "activity_type": entry.activity_type.value,
                        "activity_data": float(entry.activity_data),
                        "activity_unit": entry.activity_unit,
                        "emissions_kgco2e": float(entry.emissions_kgco2e),
                        "data_source": entry.data_source.value,
                        "emission_factor": float(entry.emission_factor),
                        "emission_factor_source": entry.emission_factor_source,
                        "calculation_method": entry.calculation_method.value,
                        "approval_status": entry.approval_status.value,
                        "quality_score": float(entry.quality_score) if entry.quality_score else None
                    }
                    for entry in entries
                ],
                "audit_logs": [
                    {
                        "event_type": log.event_type,
                        "event_description": log.event_description,
                        "event_timestamp": log.event_timestamp.isoformat(),
                        "actor_id": log.actor_id,
                        "actor_type": log.actor_type,
                        "actor_role": log.actor_role,
                        "notes": log.notes
                    }
                    for log in audit_logs
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting audit snapshot details: {e}")
            return None
    
    def get_audit_snapshots(
        self, 
        limit: int = 10, 
        offset: int = 0,
        submission_type: Optional[RegulatoryFramework] = None,
        approval_status: Optional[ApprovalStatus] = None,
        organization_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of audit snapshots with filtering"""
        try:
            query = self.db.query(EnhancedAuditSnapshot)
            
            if submission_type:
                query = query.filter(EnhancedAuditSnapshot.submission_type == submission_type)
            
            if approval_status:
                query = query.filter(EnhancedAuditSnapshot.approval_status == approval_status)
            
            if organization_id:
                query = query.filter(EnhancedAuditSnapshot.organization_id == organization_id)
            
            snapshots = query.order_by(desc(EnhancedAuditSnapshot.created_at)).offset(offset).limit(limit).all()
            
            return [
                {
                    "id": str(snapshot.id),
                    "submission_id": snapshot.submission_id,
                    "submission_type": snapshot.submission_type.value,
                    "reporting_period_start": snapshot.reporting_period_start.isoformat(),
                    "reporting_period_end": snapshot.reporting_period_end.isoformat(),
                    "total_records": snapshot.total_records,
                    "total_emissions_kgco2e": float(snapshot.total_emissions_kgco2e),
                    "approval_status": snapshot.approval_status.value,
                    "workflow_stage": snapshot.workflow_stage,
                    "created_at": snapshot.created_at.isoformat(),
                    "created_by": snapshot.created_by,
                    # Add missing required fields
                    "scope_breakdown": {
                        "scope_1": float(snapshot.scope_1_emissions or 0),
                        "scope_2": float(snapshot.scope_2_emissions or 0),
                        "scope_3": float(snapshot.scope_3_emissions or 0)
                    },
                    "compliance_metrics": {
                        "average_compliance_score": float(snapshot.average_compliance_score or 0),
                        "audit_ready_records": snapshot.audit_ready_records or 0,
                        "non_compliant_records": snapshot.non_compliant_records or 0,
                        "compliance_rate": (snapshot.audit_ready_records / snapshot.total_records * 100) if snapshot.total_records > 0 else 0
                    },
                    "description": snapshot.description or "",
                    "organization_id": snapshot.organization_id or "",
                    "business_unit": snapshot.business_unit or ""
                }
                for snapshot in snapshots
            ]
            
        except Exception as e:
            logger.error(f"Error getting audit snapshots: {e}")
            return []
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete an audit snapshot and all related data"""
        try:
            # Find the snapshot
            snapshot = self.db.query(EnhancedAuditSnapshot).filter(
                EnhancedAuditSnapshot.submission_id == snapshot_id
            ).first()
            
            if not snapshot:
                return False
            
            # Delete the snapshot (cascade will handle related entries and logs)
            self.db.delete(snapshot)
            self.db.commit()
            
            logger.info(f"Deleted enhanced audit snapshot: {snapshot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting audit snapshot {snapshot_id}: {e}")
            self.db.rollback()
            return False
