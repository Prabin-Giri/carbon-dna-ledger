"""
Enhanced Audit Snapshot API Endpoints
Comprehensive audit trail system with immutable history and rich metadata
"""
import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from .db import get_db
from .services.enhanced_audit_snapshot import (
    EnhancedAuditSnapshotService, 
    EnhancedAuditSnapshotRequest, 
    EnhancedAuditSnapshotResponse
)
from .models_enhanced_audit import (
    RegulatoryFramework, ApprovalStatus, EmissionScope, 
    ActivityType, DataSource, CalculationMethod
)
import logging

logger = logging.getLogger(__name__)

# Create router for enhanced audit endpoints
router = APIRouter(prefix="/api/audit", tags=["Enhanced Audit Snapshots"])


# Pydantic models for API requests/responses
class CreateAuditSnapshotRequest(BaseModel):
    """Request model for creating audit snapshots"""
    submission_type: RegulatoryFramework = Field(..., description="Regulatory framework type")
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
    new_status: ApprovalStatus = Field(..., description="New approval status")
    actor_role: str = Field(..., description="Role of the actor (REVIEWER, APPROVER, AUDITOR)")
    notes: Optional[str] = Field(None, description="Notes about the status change")


class AuditSnapshotEntryResponse(BaseModel):
    """Response model for audit snapshot entries"""
    id: str
    measurement_timestamp: datetime
    emission_scope: EmissionScope
    activity_type: ActivityType
    business_unit: Optional[str]
    facility_id: Optional[str]
    location: Optional[str]
    activity_data: Decimal
    activity_unit: str
    emissions_kgco2e: Decimal
    data_source: DataSource
    source_system: Optional[str]
    source_user: Optional[str]
    emission_factor: Decimal
    emission_factor_source: str
    calculation_method: CalculationMethod
    approval_status: ApprovalStatus
    quality_score: Optional[Decimal]
    uncertainty_percentage: Optional[Decimal]
    evidence_files: List[Dict[str, Any]]
    tags: List[str]
    notes: Optional[str]


class AuditSnapshotResponse(BaseModel):
    """Response model for audit snapshots"""
    id: str
    submission_id: str
    submission_type: RegulatoryFramework
    reporting_period_start: date
    reporting_period_end: date
    total_records: int
    total_emissions_kgco2e: Decimal
    scope_breakdown: Dict[str, Decimal]
    compliance_metrics: Dict[str, Any]
    approval_status: ApprovalStatus
    workflow_stage: str
    created_at: datetime
    created_by: str
    description: Optional[str]
    organization_id: Optional[str]
    business_unit: Optional[str]


class AuditLogEntryResponse(BaseModel):
    """Response model for audit log entries"""
    event_type: str
    event_description: str
    event_timestamp: datetime
    actor_id: str
    actor_type: str
    actor_role: Optional[str]
    notes: Optional[str]


class AuditSnapshotDetailsResponse(BaseModel):
    """Response model for detailed audit snapshot information"""
    snapshot: AuditSnapshotResponse
    entries: List[AuditSnapshotEntryResponse]
    audit_logs: List[AuditLogEntryResponse]


# API Endpoints

@router.post("/snapshots", response_model=Dict[str, Any])
def create_audit_snapshot(
    request: CreateAuditSnapshotRequest,
    db: Session = Depends(get_db)
):
    """Create a new enhanced audit snapshot with comprehensive metadata"""
    try:
        service = EnhancedAuditSnapshotService(db)
        
        # Convert request to service request
        service_request = EnhancedAuditSnapshotRequest(
            submission_type=request.submission_type,
            reporting_period_start=request.reporting_period_start,
            reporting_period_end=request.reporting_period_end,
            organization_id=request.organization_id,
            business_unit=request.business_unit,
            reporting_entity=request.reporting_entity,
            description=request.description,
            record_ids=request.record_ids,
            include_scope_1=request.include_scope_1,
            include_scope_2=request.include_scope_2,
            include_scope_3=request.include_scope_3,
            created_by=request.created_by
        )
        
        result = service.create_audit_snapshot(service_request)
        
        if not result.success:
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": result.message,
                    "errors": result.errors or []
                }
            )
        
        return {
            "success": True,
            "snapshot_id": result.snapshot_id,
            "submission_id": result.submission_id,
            "total_records": result.total_records,
            "total_emissions_kgco2e": float(result.total_emissions_kgco2e),
            "scope_breakdown": {
                "scope_1": float(result.scope_breakdown.get("scope_1", 0)),
                "scope_2": float(result.scope_breakdown.get("scope_2", 0)),
                "scope_3": float(result.scope_breakdown.get("scope_3", 0))
            },
            "compliance_metrics": result.compliance_metrics,
            "approval_status": result.approval_status.value,
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating audit snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots", response_model=List[AuditSnapshotResponse])
def get_audit_snapshots(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    submission_type: Optional[RegulatoryFramework] = Query(None),
    approval_status: Optional[ApprovalStatus] = Query(None),
    organization_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get list of audit snapshots with filtering options"""
    try:
        service = EnhancedAuditSnapshotService(db)
        snapshots = service.get_audit_snapshots(
            limit=limit,
            offset=offset,
            submission_type=submission_type,
            approval_status=approval_status,
            organization_id=organization_id
        )
        
        return snapshots
        
    except Exception as e:
        logger.error(f"Error getting audit snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots/{snapshot_id}", response_model=AuditSnapshotDetailsResponse)
def get_audit_snapshot_details(
    snapshot_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific audit snapshot"""
    try:
        service = EnhancedAuditSnapshotService(db)
        details = service.get_audit_snapshot_details(snapshot_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Audit snapshot not found")
        
        return details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit snapshot details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/snapshots/{snapshot_id}/approval-status")
def update_approval_status(
    snapshot_id: str,
    request: UpdateApprovalStatusRequest,
    actor_id: str = Query(..., description="ID of the user making the change"),
    db: Session = Depends(get_db)
):
    """Update the approval status of an audit snapshot"""
    try:
        service = EnhancedAuditSnapshotService(db)
        
        success = service.update_approval_status(
            snapshot_id=snapshot_id,
            new_status=request.new_status,
            actor_id=actor_id,
            actor_role=request.actor_role,
            notes=request.notes
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Audit snapshot not found")
        
        return {
            "success": True,
            "message": f"Approval status updated to {request.new_status.value}",
            "snapshot_id": snapshot_id,
            "new_status": request.new_status.value,
            "updated_by": actor_id,
            "updated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating approval status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots/{snapshot_id}/entries", response_model=List[AuditSnapshotEntryResponse])
def get_audit_snapshot_entries(
    snapshot_id: str,
    scope: Optional[EmissionScope] = Query(None),
    activity_type: Optional[ActivityType] = Query(None),
    approval_status: Optional[ApprovalStatus] = Query(None),
    db: Session = Depends(get_db)
):
    """Get entries for a specific audit snapshot with filtering"""
    try:
        service = EnhancedAuditSnapshotService(db)
        details = service.get_audit_snapshot_details(snapshot_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Audit snapshot not found")
        
        entries = details.get("entries", [])
        
        # Apply filters
        if scope:
            entries = [e for e in entries if e["emission_scope"] == scope.value]
        if activity_type:
            entries = [e for e in entries if e["activity_type"] == activity_type.value]
        if approval_status:
            entries = [e for e in entries if e["approval_status"] == approval_status.value]
        
        return entries
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit snapshot entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots/{snapshot_id}/audit-logs", response_model=List[AuditLogEntryResponse])
def get_audit_snapshot_logs(
    snapshot_id: str,
    event_type: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get audit logs for a specific audit snapshot"""
    try:
        service = EnhancedAuditSnapshotService(db)
        details = service.get_audit_snapshot_details(snapshot_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Audit snapshot not found")
        
        logs = details.get("audit_logs", [])
        
        # Apply filters
        if event_type:
            logs = [l for l in logs if l["event_type"] == event_type]
        if actor_id:
            logs = [l for l in logs if l["actor_id"] == actor_id]
        
        # Apply limit
        logs = logs[:limit]
        
        return logs
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit snapshot logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshots/{snapshot_id}/evidence")
def upload_evidence_file(
    snapshot_id: str,
    file: UploadFile = File(...),
    file_description: Optional[str] = Form(None),
    file_category: Optional[str] = Form(None),
    uploaded_by: str = Form(...),
    db: Session = Depends(get_db)
):
    """Upload evidence file for an audit snapshot"""
    try:
        # This would integrate with your file storage system
        # For now, we'll return a placeholder response
        
        return {
            "success": True,
            "message": "Evidence file uploaded successfully",
            "file_id": str(uuid.uuid4()),
            "filename": file.filename,
            "file_size": file.size,
            "snapshot_id": snapshot_id,
            "uploaded_by": uploaded_by,
            "upload_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error uploading evidence file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots/{snapshot_id}/export/json")
def export_audit_snapshot_json(
    snapshot_id: str,
    db: Session = Depends(get_db)
):
    """Export audit snapshot as JSON file"""
    try:
        service = EnhancedAuditSnapshotService(db)
        details = service.get_audit_snapshot_details(snapshot_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Audit snapshot not found")
        
        # In a real implementation, you would generate and return a file
        # For now, return the JSON data directly
        return {
            "success": True,
            "snapshot_id": snapshot_id,
            "export_timestamp": datetime.now().isoformat(),
            "data": details
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting audit snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots/{snapshot_id}/export/pdf")
def export_audit_snapshot_pdf(
    snapshot_id: str,
    db: Session = Depends(get_db)
):
    """Export audit snapshot as PDF report"""
    try:
        service = EnhancedAuditSnapshotService(db)
        details = service.get_audit_snapshot_details(snapshot_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Audit snapshot not found")
        
        # In a real implementation, you would generate a PDF and return it
        # For now, return a placeholder response
        return {
            "success": True,
            "message": "PDF export initiated",
            "snapshot_id": snapshot_id,
            "export_timestamp": datetime.now().isoformat(),
            "download_url": f"/api/audit/snapshots/{snapshot_id}/download/pdf"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting audit snapshot PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots/{snapshot_id}/compliance-check")
def run_compliance_check(
    snapshot_id: str,
    framework: Optional[RegulatoryFramework] = Query(None),
    db: Session = Depends(get_db)
):
    """Run compliance check for an audit snapshot"""
    try:
        service = EnhancedAuditSnapshotService(db)
        details = service.get_audit_snapshot_details(snapshot_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Audit snapshot not found")
        
        # In a real implementation, you would run comprehensive compliance checks
        # For now, return a placeholder response
        snapshot = details.get("snapshot", {})
        
        compliance_results = {
            "snapshot_id": snapshot_id,
            "framework": framework.value if framework else snapshot.get("submission_type"),
            "compliance_score": snapshot.get("compliance_metrics", {}).get("average_compliance_score", 0),
            "audit_ready": snapshot.get("compliance_metrics", {}).get("audit_ready_records", 0),
            "total_records": snapshot.get("total_records", 0),
            "compliance_rate": snapshot.get("compliance_metrics", {}).get("compliance_rate", 0),
            "issues": [],
            "recommendations": [],
            "check_timestamp": datetime.now().isoformat()
        }
        
        # Add some sample issues and recommendations
        if compliance_results["compliance_rate"] < 90:
            compliance_results["issues"].append("Low compliance rate - review data quality")
            compliance_results["recommendations"].append("Improve data collection processes")
        
        if snapshot.get("total_records", 0) == 0:
            compliance_results["issues"].append("No emission records found")
            compliance_results["recommendations"].append("Add emission data before submission")
        
        return compliance_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running compliance check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frameworks", response_model=List[Dict[str, str]])
def get_supported_frameworks():
    """Get list of supported regulatory frameworks"""
    return [
        {"value": framework.value, "label": framework.value.upper(), "description": f"{framework.value.upper()} regulatory framework"}
        for framework in RegulatoryFramework
    ]


@router.get("/scopes", response_model=List[Dict[str, str]])
def get_emission_scopes():
    """Get list of emission scopes"""
    return [
        {"value": scope.value, "label": scope.value.replace("_", " ").title(), "description": f"{scope.value.replace('_', ' ').title()} emissions"}
        for scope in EmissionScope
    ]


@router.get("/activity-types", response_model=List[Dict[str, str]])
def get_activity_types():
    """Get list of activity types"""
    return [
        {"value": activity.value, "label": activity.value.replace("_", " ").title(), "description": f"{activity.value.replace('_', ' ').title()} activity"}
        for activity in ActivityType
    ]


@router.get("/approval-statuses", response_model=List[Dict[str, str]])
def get_approval_statuses():
    """Get list of approval statuses"""
    return [
        {"value": status.value, "label": status.value.replace("_", " ").title(), "description": f"{status.value.replace('_', ' ').title()} status"}
        for status in ApprovalStatus
    ]


@router.delete("/snapshots/{snapshot_id}")
def delete_audit_snapshot(
    snapshot_id: str,
    db: Session = Depends(get_db)
):
    """Delete an enhanced audit snapshot"""
    try:
        service = EnhancedAuditSnapshotService(db)
        success = service.delete_snapshot(snapshot_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Audit snapshot not found")
        
        return {
            "success": True,
            "message": f"Enhanced audit snapshot {snapshot_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting enhanced audit snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))
