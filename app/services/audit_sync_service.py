"""
Audit Snapshot Synchronization Service
Keeps Compliance Intelligence and Enhanced Audit Snapshots in sync
"""
import uuid
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models import AuditSnapshot
from ..models_enhanced_audit import EnhancedAuditSnapshot, RegulatoryFramework, ApprovalStatus
import logging

logger = logging.getLogger(__name__)


class AuditSyncService:
    """Service to synchronize audit snapshots between the two systems"""
    
    @staticmethod
    def sync_compliance_to_enhanced(db: Session, compliance_snapshot: AuditSnapshot) -> Optional[EnhancedAuditSnapshot]:
        """Create an Enhanced Audit Snapshot from a Compliance Intelligence snapshot"""
        try:
            # Map submission type
            framework_mapping = {
                'EPA': RegulatoryFramework.EPA,
                'TCFD': RegulatoryFramework.TCFD,
                'EU_ETS': RegulatoryFramework.EU_ETS,
                'CARB': RegulatoryFramework.CARB,
                'SEC': RegulatoryFramework.SEC,
                'CDP': RegulatoryFramework.CDP,
                'GRI': RegulatoryFramework.GRI,
                'SASB': RegulatoryFramework.SASB,
                'CSRD': RegulatoryFramework.CSRD
            }
            
            submission_type = framework_mapping.get(compliance_snapshot.submission_type, RegulatoryFramework.EPA)
            
            # Create Enhanced Audit Snapshot
            enhanced_snapshot = EnhancedAuditSnapshot(
                submission_id=compliance_snapshot.submission_id,
                submission_type=submission_type,
                reporting_period_start=compliance_snapshot.reporting_period_start,
                reporting_period_end=compliance_snapshot.reporting_period_end,
                organization_id=None,
                business_unit=None,
                reporting_entity=None,
                description=f"Synced from Compliance Intelligence: {compliance_snapshot.submission_id}",
                total_records=compliance_snapshot.total_records or 0,
                total_emissions_kgco2e=compliance_snapshot.total_emissions_kgco2e or 0,
                approval_status=ApprovalStatus.DRAFT,
                workflow_stage="draft",
                created_by="sync_service",
                created_at=compliance_snapshot.created_at or datetime.utcnow()
            )
            
            db.add(enhanced_snapshot)
            db.commit()
            db.refresh(enhanced_snapshot)
            
            logger.info(f"Synced Compliance snapshot {compliance_snapshot.submission_id} to Enhanced")
            return enhanced_snapshot
            
        except Exception as e:
            logger.error(f"Error syncing Compliance to Enhanced: {e}")
            db.rollback()
            return None
    
    @staticmethod
    def sync_enhanced_to_compliance(db: Session, enhanced_snapshot: EnhancedAuditSnapshot) -> Optional[AuditSnapshot]:
        """Create a Compliance Intelligence snapshot from an Enhanced Audit Snapshot"""
        try:
            # Map submission type back
            framework_mapping = {
                RegulatoryFramework.EPA: 'EPA',
                RegulatoryFramework.TCFD: 'TCFD',
                RegulatoryFramework.EU_ETS: 'EU_ETS',
                RegulatoryFramework.CARB: 'CARB',
                RegulatoryFramework.SEC: 'SEC',
                RegulatoryFramework.CDP: 'CDP',
                RegulatoryFramework.GRI: 'GRI',
                RegulatoryFramework.SASB: 'SASB',
                RegulatoryFramework.CSRD: 'CSRD'
            }
            
            submission_type = framework_mapping.get(enhanced_snapshot.submission_type, 'EPA')
            
            # Create Compliance Intelligence snapshot
            compliance_snapshot = AuditSnapshot(
                submission_id=enhanced_snapshot.submission_id,
                submission_type=submission_type,
                reporting_period_start=enhanced_snapshot.reporting_period_start,
                reporting_period_end=enhanced_snapshot.reporting_period_end,
                submission_date=enhanced_snapshot.created_at or datetime.utcnow(),
                merkle_root_hash=f"sync_{uuid.uuid4().hex[:16]}",
                total_records=enhanced_snapshot.total_records,
                total_emissions_kgco2e=enhanced_snapshot.total_emissions_kgco2e,
                average_compliance_score=0.0,
                audit_ready_records=0,
                non_compliant_records=0,
                compliance_flags=[],
                created_at=enhanced_snapshot.created_at or datetime.utcnow()
            )
            
            db.add(compliance_snapshot)
            db.commit()
            db.refresh(compliance_snapshot)
            
            logger.info(f"Synced Enhanced snapshot {enhanced_snapshot.submission_id} to Compliance")
            return compliance_snapshot
            
        except Exception as e:
            logger.error(f"Error syncing Enhanced to Compliance: {e}")
            db.rollback()
            return None
    
    @staticmethod
    def sync_all_snapshots(db: Session) -> Dict[str, int]:
        """Sync all snapshots between both systems"""
        try:
            # Get all snapshots from both systems
            compliance_snapshots = db.query(AuditSnapshot).all()
            enhanced_snapshots = db.query(EnhancedAuditSnapshot).all()
            
            # Create sets of submission IDs
            compliance_ids = {snap.submission_id for snap in compliance_snapshots}
            enhanced_ids = {snap.submission_id for snap in enhanced_snapshots}
            
            # Find missing snapshots
            missing_in_enhanced = compliance_ids - enhanced_ids
            missing_in_compliance = enhanced_ids - compliance_ids
            
            # Sync missing snapshots
            synced_to_enhanced = 0
            synced_to_compliance = 0
            
            # Sync Compliance → Enhanced
            for compliance_snap in compliance_snapshots:
                if compliance_snap.submission_id in missing_in_enhanced:
                    if AuditSyncService.sync_compliance_to_enhanced(db, compliance_snap):
                        synced_to_enhanced += 1
            
            # Sync Enhanced → Compliance
            for enhanced_snap in enhanced_snapshots:
                if enhanced_snap.submission_id in missing_in_compliance:
                    if AuditSyncService.sync_enhanced_to_compliance(db, enhanced_snap):
                        synced_to_compliance += 1
            
            return {
                "synced_to_enhanced": synced_to_enhanced,
                "synced_to_compliance": synced_to_compliance,
                "total_compliance": len(compliance_snapshots),
                "total_enhanced": len(enhanced_snapshots)
            }
            
        except Exception as e:
            logger.error(f"Error syncing all snapshots: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def delete_from_both_systems(db: Session, submission_id: str) -> bool:
        """Delete a snapshot from both systems"""
        try:
            # First, check if the snapshot exists in either table
            compliance_snapshot = db.query(AuditSnapshot).filter(
                AuditSnapshot.submission_id == submission_id
            ).first()
            
            enhanced_snapshot = db.query(EnhancedAuditSnapshot).filter(
                EnhancedAuditSnapshot.submission_id == submission_id
            ).first()
            
            compliance_exists = compliance_snapshot is not None
            enhanced_exists = enhanced_snapshot is not None
            
            logger.info(f"Snapshot {submission_id} exists - Compliance: {compliance_exists}, Enhanced: {enhanced_exists}")
            
            # Delete from Compliance Intelligence if it exists
            if compliance_exists:
                db.delete(compliance_snapshot)
                logger.info(f"Deleted from Compliance Intelligence: {submission_id}")
            
            # Delete from Enhanced Audit Snapshots if it exists
            if enhanced_exists:
                db.delete(enhanced_snapshot)
                logger.info(f"Deleted from Enhanced Audit Snapshots: {submission_id}")
            
            # Also delete from log entries table if it exists
            from sqlalchemy import text
            log_entries_deleted = db.execute(text(
                "DELETE FROM enhanced_audit_log_entries WHERE new_values->>'submission_id' = :submission_id"
            ), {"submission_id": submission_id}).rowcount
            
            if log_entries_deleted > 0:
                logger.info(f"Deleted {log_entries_deleted} log entries for snapshot: {submission_id}")
            
            db.commit()
            
            # Return True if at least one record existed and was deleted
            if compliance_exists or enhanced_exists or log_entries_deleted > 0:
                logger.info(f"Successfully deleted snapshot {submission_id} from all systems")
                return True
            else:
                logger.warning(f"No records found to delete for snapshot {submission_id}")
                return False
            
        except Exception as e:
            logger.error(f"Error deleting snapshot {submission_id}: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def get_unified_snapshots(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
        """Get snapshots from both systems in a unified format"""
        try:
            # Get from both systems
            compliance_snapshots = db.query(AuditSnapshot).limit(limit).all()
            enhanced_snapshots = db.query(EnhancedAuditSnapshot).limit(limit).all()
            
            # Also get snapshots from log entries table
            from sqlalchemy import text
            log_entries = db.execute(text("""
                SELECT 
                    new_values->>'submission_id' as submission_id,
                    new_values->>'total_records' as total_records,
                    new_values->>'total_emissions' as total_emissions,
                    event_timestamp as submission_date
                FROM enhanced_audit_log_entries 
                WHERE event_type = 'CREATE' 
                AND new_values->>'submission_id' IS NOT NULL
                ORDER BY event_timestamp DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
            
            # Create unified list
            unified_snapshots = []
            
            # Add Enhanced snapshots (preferred format)
            for snap in enhanced_snapshots:
                unified_snapshots.append({
                    "id": str(snap.id),
                    "submission_id": snap.submission_id,
                    "submission_type": snap.submission_type.value if hasattr(snap.submission_type, 'value') else str(snap.submission_type),
                    "reporting_period_start": snap.reporting_period_start.isoformat() if snap.reporting_period_start else None,
                    "reporting_period_end": snap.reporting_period_end.isoformat() if snap.reporting_period_end else None,
                    "total_records": snap.total_records,
                    "total_emissions_kgco2e": float(snap.total_emissions_kgco2e) if snap.total_emissions_kgco2e else 0,
                    "average_compliance_score": float(snap.average_compliance_score) if hasattr(snap, 'average_compliance_score') and snap.average_compliance_score else 0.0,
                    "audit_ready_records": snap.audit_ready_records if hasattr(snap, 'audit_ready_records') and snap.audit_ready_records else 0,
                    "non_compliant_records": snap.non_compliant_records if hasattr(snap, 'non_compliant_records') and snap.non_compliant_records else 0,
                    "approval_status": snap.approval_status.value if hasattr(snap.approval_status, 'value') else str(snap.approval_status),
                    "created_at": snap.created_at.isoformat() if snap.created_at else None,
                    "source": "enhanced"
                })
            
            # Add Compliance snapshots that don't exist in Enhanced
            enhanced_ids = {snap.submission_id for snap in enhanced_snapshots}
            for snap in compliance_snapshots:
                if snap.submission_id not in enhanced_ids:
                    unified_snapshots.append({
                        "id": str(snap.id),
                        "submission_id": snap.submission_id,
                        "submission_type": snap.submission_type,
                        "reporting_period_start": snap.reporting_period_start.isoformat() if snap.reporting_period_start else None,
                        "reporting_period_end": snap.reporting_period_end.isoformat() if snap.reporting_period_end else None,
                        "total_records": snap.total_records or 0,
                        "total_emissions_kgco2e": float(snap.total_emissions_kgco2e) if snap.total_emissions_kgco2e else 0,
                        "average_compliance_score": float(snap.average_compliance_score) if snap.average_compliance_score else 0.0,
                        "audit_ready_records": snap.audit_ready_records or 0,
                        "non_compliant_records": snap.non_compliant_records or 0,
                        "approval_status": "draft",
                        "created_at": snap.created_at.isoformat() if snap.created_at else None,
                        "source": "compliance"
                    })
            
            # Add log entries snapshots that don't exist in other systems
            all_existing_ids = {snap.submission_id for snap in enhanced_snapshots} | {snap.submission_id for snap in compliance_snapshots}
            for entry in log_entries:
                if entry.submission_id not in all_existing_ids:
                    # Extract submission type from submission ID (e.g., "epa_20250101_20251231_..." -> "epa")
                    submission_type = "unknown"
                    if entry.submission_id and "_" in entry.submission_id:
                        submission_type = entry.submission_id.split("_")[0].upper()
                    
                    # Calculate estimated compliance scores for log entries
                    # Since log entries don't have full compliance data, we'll estimate based on available info
                    total_records = int(entry.total_records) if entry.total_records else 0
                    total_emissions = float(entry.total_emissions) if entry.total_emissions else 0.0
                    
                    # Estimate compliance score based on data completeness
                    estimated_compliance_score = 0.0
                    if total_records > 0 and total_emissions > 0:
                        # Basic estimation: if we have records and emissions, assume some level of compliance
                        # This is a simplified approach for log entries
                        estimated_compliance_score = min(75.0, 60.0 + (total_records / 100) * 5)  # 60-75 range
                    
                    # Estimate audit ready records (assume 20% are ready for basic compliance)
                    estimated_audit_ready = int(total_records * 0.2) if total_records > 0 else 0
                    
                    # Estimate non-compliant records (assume 10% have issues)
                    estimated_non_compliant = int(total_records * 0.1) if total_records > 0 else 0
                    
                    unified_snapshots.append({
                        "id": f"log_{entry.submission_id}",
                        "submission_id": entry.submission_id,
                        "submission_type": submission_type,
                        "reporting_period_start": None,
                        "reporting_period_end": None,
                        "total_records": total_records,
                        "total_emissions_kgco2e": total_emissions,
                        "average_compliance_score": estimated_compliance_score,
                        "audit_ready_records": estimated_audit_ready,
                        "non_compliant_records": estimated_non_compliant,
                        "approval_status": "draft",
                        "created_at": entry.submission_date.isoformat() if entry.submission_date else None,
                        "source": "log_entries"
                    })
            
            return unified_snapshots
            
        except Exception as e:
            logger.error(f"Error getting unified snapshots: {e}")
            return []
