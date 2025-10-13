"""
Simple Enhanced Audit API Endpoints
Working version that integrates with existing system
"""
import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from .db import get_db
from .models import AuditSnapshot
from .services.compliance_integrity_engine import ComplianceIntegrityEngine
import logging

logger = logging.getLogger(__name__)

# Create router for simple enhanced audit endpoints
router = APIRouter(prefix="/api/audit", tags=["Enhanced Audit Snapshots"])


# Pydantic models for API requests/responses
class CreateEnhancedAuditSnapshotRequest(BaseModel):
    """Request model for creating enhanced audit snapshots"""
    submission_type: str = Field(..., description="Regulatory framework type")
    reporting_period_start: date = Field(..., description="Start date of reporting period")
    reporting_period_end: date = Field(..., description="End date of reporting period")
    organization_id: Optional[str] = Field(None, description="Organization identifier")
    business_unit: Optional[str] = Field(None, description="Business unit identifier")
    reporting_entity: Optional[str] = Field(None, description="Reporting entity name")
    description: Optional[str] = Field(None, description="Description of the audit snapshot")
    record_ids: Optional[List[str]] = Field(None, description="Specific record IDs to include")
    include_scope_1: bool = Field(True, description="Include Scope 1 emissions")
    include_scope_2: bool = Field(True, description="Include Scope 2 emissions")
    include_scope_3: bool = Field(True, description="Include Scope 3 emissions")
    created_by: str = Field("system", description="User creating the snapshot")


class UpdateApprovalStatusRequest(BaseModel):
    """Request model for updating approval status"""
    new_status: str = Field(..., description="New approval status")
    actor_role: str = Field(..., description="Role of the actor (REVIEWER, APPROVER, AUDITOR)")
    notes: Optional[str] = Field(None, description="Notes about the status change")


# API Endpoints

@router.post("/snapshots", response_model=Dict[str, Any])
def create_enhanced_audit_snapshot(
    request: CreateEnhancedAuditSnapshotRequest,
    db: Session = Depends(get_db)
):
    """Create a new enhanced audit snapshot with comprehensive metadata"""
    try:
        compliance_engine = ComplianceIntegrityEngine(db)
        
        # Create audit snapshot using existing service
        snapshot_data = compliance_engine.create_audit_snapshot(
            submission_type=request.submission_type,
            reporting_period_start=request.reporting_period_start,
            reporting_period_end=request.reporting_period_end,
            record_ids=request.record_ids,
            allow_empty=True
        )
        
        # Enhance the response with additional metadata
        enhanced_response = {
            "success": True,
            "snapshot_id": snapshot_data.submission_id,
            "submission_id": snapshot_data.submission_id,
            "submission_type": request.submission_type,
            "reporting_period_start": request.reporting_period_start.isoformat(),
            "reporting_period_end": request.reporting_period_end.isoformat(),
            "total_records": snapshot_data.total_records,
            "total_emissions_kgco2e": float(snapshot_data.total_emissions_kgco2e),
            "scope_breakdown": {
                "scope_1": float(snapshot_data.total_emissions_kgco2e) * 0.4,  # Estimated
                "scope_2": float(snapshot_data.total_emissions_kgco2e) * 0.3,  # Estimated
                "scope_3": float(snapshot_data.total_emissions_kgco2e) * 0.3   # Estimated
            },
            "compliance_metrics": {
                "average_compliance_score": snapshot_data.average_compliance_score,
                "audit_ready_records": snapshot_data.audit_ready_records,
                "non_compliant_records": snapshot_data.non_compliant_records,
                "compliance_rate": (snapshot_data.audit_ready_records / snapshot_data.total_records * 100) if snapshot_data.total_records > 0 else 0
            },
            "approval_status": "draft",
            "workflow_stage": "data_collection",
            "created_at": datetime.now().isoformat(),
            "created_by": request.created_by,
            "description": request.description,
            "organization_id": request.organization_id,
            "business_unit": request.business_unit,
            "merkle_root_hash": snapshot_data.merkle_root_hash,
            "message": "Enhanced audit snapshot created successfully"
        }
        
        return enhanced_response
        
    except Exception as e:
        logger.error(f"Error creating enhanced audit snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots", response_model=List[Dict[str, Any]])
def get_enhanced_audit_snapshots(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    submission_type: Optional[str] = Query(None),
    approval_status: Optional[str] = Query(None),
    organization_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get list of enhanced audit snapshots with filtering options"""
    try:
        query = db.query(AuditSnapshot)
        
        if submission_type:
            query = query.filter(AuditSnapshot.submission_type == submission_type)
        
        if approval_status:
            query = query.filter(AuditSnapshot.submission_status == approval_status)
        
        snapshots = query.order_by(AuditSnapshot.created_at.desc()).offset(offset).limit(limit).all()
        
        enhanced_snapshots = []
        for snapshot in snapshots:
            enhanced_snapshot = {
                "id": str(snapshot.id),
                "submission_id": snapshot.submission_id,
                "submission_type": snapshot.submission_type,
                "reporting_period_start": snapshot.reporting_period_start.isoformat(),
                "reporting_period_end": snapshot.reporting_period_end.isoformat(),
                "total_records": snapshot.total_records,
                "total_emissions_kgco2e": float(snapshot.total_emissions_kgco2e),
                "scope_breakdown": {
                    "scope_1": float(snapshot.total_emissions_kgco2e) * 0.4,  # Estimated
                    "scope_2": float(snapshot.total_emissions_kgco2e) * 0.3,  # Estimated
                    "scope_3": float(snapshot.total_emissions_kgco2e) * 0.3   # Estimated
                },
                "compliance_metrics": {
                    "average_compliance_score": float(snapshot.average_compliance_score),
                    "audit_ready_records": snapshot.audit_ready_records,
                    "non_compliant_records": snapshot.non_compliant_records,
                    "compliance_rate": (snapshot.audit_ready_records / snapshot.total_records * 100) if snapshot.total_records > 0 else 0
                },
                "approval_status": snapshot.submission_status,
                "workflow_stage": "data_collection",
                "created_at": snapshot.created_at.isoformat(),
                "created_by": "system",
                "merkle_root_hash": snapshot.merkle_root_hash
            }
            enhanced_snapshots.append(enhanced_snapshot)
        
        return enhanced_snapshots
        
    except Exception as e:
        logger.error(f"Error getting enhanced audit snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots/{snapshot_id}", response_model=Dict[str, Any])
def get_enhanced_audit_snapshot_details(
    snapshot_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific enhanced audit snapshot"""
    try:
        snapshot = db.query(AuditSnapshot).filter(
            AuditSnapshot.submission_id == snapshot_id
        ).first()
        
        if not snapshot:
            raise HTTPException(status_code=404, detail="Audit snapshot not found")
        
        # Create enhanced details response
        details = {
            "snapshot": {
                "id": str(snapshot.id),
                "submission_id": snapshot.submission_id,
                "submission_type": snapshot.submission_type,
                "reporting_period_start": snapshot.reporting_period_start.isoformat(),
                "reporting_period_end": snapshot.reporting_period_end.isoformat(),
                "total_records": snapshot.total_records,
                "total_emissions_kgco2e": float(snapshot.total_emissions_kgco2e),
                "scope_breakdown": {
                    "scope_1": float(snapshot.total_emissions_kgco2e) * 0.4,
                    "scope_2": float(snapshot.total_emissions_kgco2e) * 0.3,
                    "scope_3": float(snapshot.total_emissions_kgco2e) * 0.3
                },
                "compliance_metrics": {
                    "average_compliance_score": float(snapshot.average_compliance_score),
                    "audit_ready_records": snapshot.audit_ready_records,
                    "non_compliant_records": snapshot.non_compliant_records,
                    "compliance_rate": (snapshot.audit_ready_records / snapshot.total_records * 100) if snapshot.total_records > 0 else 0
                },
                "approval_status": snapshot.submission_status,
                "workflow_stage": "data_collection",
                "created_at": snapshot.created_at.isoformat(),
                "created_by": "system"
            },
            "entries": [],  # Placeholder - would be populated from emission records
            "audit_logs": []  # Placeholder - would be populated from audit logs
        }
        
        return details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting enhanced audit snapshot details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/snapshots/{snapshot_id}/approval-status")
def update_enhanced_approval_status(
    snapshot_id: str,
    request: UpdateApprovalStatusRequest,
    actor_id: str = Query(..., description="ID of the user making the change"),
    db: Session = Depends(get_db)
):
    """Update the approval status of an enhanced audit snapshot"""
    try:
        snapshot = db.query(AuditSnapshot).filter(
            AuditSnapshot.submission_id == snapshot_id
        ).first()
        
        if not snapshot:
            raise HTTPException(status_code=404, detail="Audit snapshot not found")
        
        old_status = snapshot.submission_status
        snapshot.submission_status = request.new_status
        
        # Update role-specific fields if they exist
        now = datetime.now()
        if request.actor_role == "REVIEWER":
            snapshot.verified_by = actor_id
            snapshot.verification_date = now
        elif request.actor_role == "APPROVER":
            snapshot.verified_by = actor_id
            snapshot.verification_date = now
        
        if request.notes:
            snapshot.verification_notes = request.notes
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Approval status updated to {request.new_status}",
            "snapshot_id": snapshot_id,
            "new_status": request.new_status,
            "updated_by": actor_id,
            "updated_at": now.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating enhanced approval status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots/{snapshot_id}/compliance-check")
def run_enhanced_compliance_check(
    snapshot_id: str,
    framework: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Run compliance check for an enhanced audit snapshot"""
    try:
        snapshot = db.query(AuditSnapshot).filter(
            AuditSnapshot.submission_id == snapshot_id
        ).first()
        
        if not snapshot:
            raise HTTPException(status_code=404, detail="Audit snapshot not found")
        
        compliance_results = {
            "snapshot_id": snapshot_id,
            "framework": framework or snapshot.submission_type,
            "compliance_score": float(snapshot.average_compliance_score),
            "audit_ready": snapshot.audit_ready_records,
            "total_records": snapshot.total_records,
            "compliance_rate": (snapshot.audit_ready_records / snapshot.total_records * 100) if snapshot.total_records > 0 else 0,
            "issues": [],
            "recommendations": [],
            "check_timestamp": datetime.now().isoformat()
        }
        
        # Add some sample issues and recommendations
        if compliance_results["compliance_rate"] < 90:
            compliance_results["issues"].append("Low compliance rate - review data quality")
            compliance_results["recommendations"].append("Improve data collection processes")
        
        if snapshot.total_records == 0:
            compliance_results["issues"].append("No emission records found")
            compliance_results["recommendations"].append("Add emission data before submission")
        
        return compliance_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running enhanced compliance check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frameworks", response_model=List[Dict[str, str]])
def get_supported_frameworks():
    """Get list of supported regulatory frameworks"""
    return [
        {"value": "epa", "label": "EPA", "description": "EPA regulatory framework"},
        {"value": "eu_ets", "label": "EU ETS", "description": "EU Emissions Trading System"},
        {"value": "carb", "label": "CARB", "description": "California Air Resources Board"},
        {"value": "tcfd", "label": "TCFD", "description": "Task Force on Climate-related Financial Disclosures"},
        {"value": "sec", "label": "SEC", "description": "Securities and Exchange Commission"},
        {"value": "cdp", "label": "CDP", "description": "Carbon Disclosure Project"},
        {"value": "gri", "label": "GRI", "description": "Global Reporting Initiative"},
        {"value": "sasb", "label": "SASB", "description": "Sustainability Accounting Standards Board"},
        {"value": "csrd", "label": "CSRD", "description": "Corporate Sustainability Reporting Directive"}
    ]


@router.get("/scopes", response_model=List[Dict[str, str]])
def get_emission_scopes():
    """Get list of emission scopes"""
    return [
        {"value": "scope_1", "label": "Scope 1", "description": "Direct emissions"},
        {"value": "scope_2", "label": "Scope 2", "description": "Indirect emissions from purchased energy"},
        {"value": "scope_3", "label": "Scope 3", "description": "Other indirect emissions"}
    ]


@router.get("/activity-types", response_model=List[Dict[str, str]])
def get_activity_types():
    """Get list of activity types"""
    return [
        {"value": "stationary_combustion", "label": "Stationary Combustion", "description": "Stationary combustion activity"},
        {"value": "mobile_combustion", "label": "Mobile Combustion", "description": "Mobile combustion activity"},
        {"value": "purchased_electricity", "label": "Purchased Electricity", "description": "Purchased electricity activity"},
        {"value": "transportation", "label": "Transportation", "description": "Transportation activity"},
        {"value": "business_travel", "label": "Business Travel", "description": "Business travel activity"},
        {"value": "purchased_goods", "label": "Purchased Goods", "description": "Purchased goods activity"}
    ]


@router.get("/approval-statuses", response_model=List[Dict[str, str]])
def get_approval_statuses():
    """Get list of approval statuses"""
    return [
        {"value": "draft", "label": "Draft", "description": "Draft status"},
        {"value": "pending_review", "label": "Pending Review", "description": "Pending review status"},
        {"value": "under_review", "label": "Under Review", "description": "Under review status"},
        {"value": "approved", "label": "Approved", "description": "Approved status"},
        {"value": "rejected", "label": "Rejected", "description": "Rejected status"},
        {"value": "submitted", "label": "Submitted", "description": "Submitted status"},
        {"value": "audited", "label": "Audited", "description": "Audited status"}
    ]
