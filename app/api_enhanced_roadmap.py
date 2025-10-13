"""
Enhanced Compliance Roadmap API Endpoints
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from .db import get_db
from .services.enhanced_compliance_roadmap import EnhancedComplianceRoadmapService
import logging

logger = logging.getLogger(__name__)

# Create router for enhanced compliance roadmap
router = APIRouter(prefix="/api/compliance", tags=["Enhanced Compliance Roadmap"])

# Pydantic models
class ComplianceRequirementResponse(BaseModel):
    """Response model for compliance requirements"""
    requirement_id: str
    title: str
    description: str
    category: str
    priority: str
    estimated_cost: float
    estimated_time_days: int
    dependencies: List[str]
    deliverables: List[str]
    success_criteria: List[str]
    regulatory_reference: str

class ActionableStepResponse(BaseModel):
    """Response model for actionable steps"""
    step_id: str
    title: str
    description: str
    requirement_id: str
    framework: str
    estimated_hours: int
    resources_needed: List[str]
    prerequisites: List[str]
    deliverables: List[str]
    validation_criteria: List[str]

class EnhancedRoadmapRequest(BaseModel):
    """Request model for enhanced roadmap generation"""
    frameworks: List[str] = Field(..., description="List of regulatory frameworks")
    budget_constraint: float = Field(100000, description="Budget constraint in USD")
    timeline_months: int = Field(12, description="Timeline in months")

class EnhancedRoadmapResponse(BaseModel):
    """Response model for enhanced roadmap"""
    frameworks: List[str]
    total_budget: float
    timeline_months: int
    requirements: List[ComplianceRequirementResponse]
    actionable_steps: List[ActionableStepResponse]
    priority_sequence: List[str]
    risk_assessment: Dict[str, Any]
    resource_requirements: Dict[str, Any]
    success_metrics: Dict[str, Any]
    generated_at: str

# API Endpoints

@router.post("/enhanced-roadmap", response_model=EnhancedRoadmapResponse)
def generate_enhanced_compliance_roadmap(
    request: EnhancedRoadmapRequest,
    db: Session = Depends(get_db)
):
    """Generate enhanced compliance roadmap with detailed requirements and actionable steps"""
    try:
        service = EnhancedComplianceRoadmapService(db)
        
        roadmap = service.generate_enhanced_roadmap(
            frameworks=request.frameworks,
            budget_constraint=request.budget_constraint,
            timeline_months=request.timeline_months
        )
        
        # Convert to response format
        requirements_response = [
            ComplianceRequirementResponse(
                requirement_id=req.requirement_id,
                title=req.title,
                description=req.description,
                category=req.category,
                priority=req.priority,
                estimated_cost=req.estimated_cost,
                estimated_time_days=req.estimated_time_days,
                dependencies=req.dependencies,
                deliverables=req.deliverables,
                success_criteria=req.success_criteria,
                regulatory_reference=req.regulatory_reference
            )
            for req in roadmap.requirements
        ]
        
        steps_response = [
            ActionableStepResponse(
                step_id=step.step_id,
                title=step.title,
                description=step.description,
                requirement_id=step.requirement_id,
                framework=step.framework,
                estimated_hours=step.estimated_hours,
                resources_needed=step.resources_needed,
                prerequisites=step.prerequisites,
                deliverables=step.deliverables,
                validation_criteria=step.validation_criteria
            )
            for step in roadmap.actionable_steps
        ]
        
        return EnhancedRoadmapResponse(
            frameworks=roadmap.frameworks,
            total_budget=roadmap.total_budget,
            timeline_months=roadmap.timeline_months,
            requirements=requirements_response,
            actionable_steps=steps_response,
            priority_sequence=roadmap.priority_sequence,
            risk_assessment=roadmap.risk_assessment,
            resource_requirements=roadmap.resource_requirements,
            success_metrics=roadmap.success_metrics,
            generated_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error generating enhanced compliance roadmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/roadmap/requirements/{framework}")
def get_framework_requirements(
    framework: str,
    db: Session = Depends(get_db)
):
    """Get detailed requirements for a specific framework"""
    try:
        service = EnhancedComplianceRoadmapService(db)
        
        # Generate requirements for single framework
        roadmap = service.generate_enhanced_roadmap([framework], 50000, 6)
        
        return {
            "framework": framework,
            "requirements": [
                {
                    "requirement_id": req.requirement_id,
                    "title": req.title,
                    "description": req.description,
                    "category": req.category,
                    "priority": req.priority,
                    "estimated_cost": req.estimated_cost,
                    "estimated_time_days": req.estimated_time_days,
                    "dependencies": req.dependencies,
                    "deliverables": req.deliverables,
                    "success_criteria": req.success_criteria,
                    "regulatory_reference": req.regulatory_reference
                }
                for req in roadmap.requirements
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting framework requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/roadmap/actionable-steps/{requirement_id}")
def get_requirement_actionable_steps(
    requirement_id: str,
    db: Session = Depends(get_db)
):
    """Get actionable steps for a specific requirement"""
    try:
        service = EnhancedComplianceRoadmapService(db)
        
        # Generate roadmap to get steps
        roadmap = service.generate_enhanced_roadmap(['EPA', 'EU_ETS', 'TCFD'], 100000, 12)
        
        # Filter steps for the specific requirement
        relevant_steps = [
            step for step in roadmap.actionable_steps 
            if step.requirement_id == requirement_id
        ]
        
        return {
            "requirement_id": requirement_id,
            "actionable_steps": [
                {
                    "step_id": step.step_id,
                    "title": step.title,
                    "description": step.description,
                    "framework": step.framework,
                    "estimated_hours": step.estimated_hours,
                    "resources_needed": step.resources_needed,
                    "prerequisites": step.prerequisites,
                    "deliverables": step.deliverables,
                    "validation_criteria": step.validation_criteria
                }
                for step in relevant_steps
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting actionable steps: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/roadmap/risk-assessment")
def get_compliance_risk_assessment(
    frameworks: Optional[str] = Query(None, description="Comma-separated list of frameworks"),
    db: Session = Depends(get_db)
):
    """Get compliance risk assessment for frameworks"""
    try:
        service = EnhancedComplianceRoadmapService(db)
        
        framework_list = frameworks.split(',') if frameworks else ['EPA', 'EU_ETS', 'TCFD']
        
        roadmap = service.generate_enhanced_roadmap(framework_list, 100000, 12)
        
        return {
            "frameworks": framework_list,
            "risk_assessment": roadmap.risk_assessment,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting risk assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/roadmap/resource-requirements")
def get_resource_requirements(
    frameworks: Optional[str] = Query(None, description="Comma-separated list of frameworks"),
    budget_constraint: float = Query(100000, description="Budget constraint in USD"),
    db: Session = Depends(get_db)
):
    """Get resource requirements for compliance roadmap"""
    try:
        service = EnhancedComplianceRoadmapService(db)
        
        framework_list = frameworks.split(',') if frameworks else ['EPA', 'EU_ETS', 'TCFD']
        
        roadmap = service.generate_enhanced_roadmap(framework_list, budget_constraint, 12)
        
        return {
            "frameworks": framework_list,
            "budget_constraint": budget_constraint,
            "resource_requirements": roadmap.resource_requirements,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting resource requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/roadmap/success-metrics")
def get_success_metrics(
    frameworks: Optional[str] = Query(None, description="Comma-separated list of frameworks"),
    db: Session = Depends(get_db)
):
    """Get success metrics for compliance roadmap"""
    try:
        service = EnhancedComplianceRoadmapService(db)
        
        framework_list = frameworks.split(',') if frameworks else ['EPA', 'EU_ETS', 'TCFD']
        
        roadmap = service.generate_enhanced_roadmap(framework_list, 100000, 12)
        
        return {
            "frameworks": framework_list,
            "success_metrics": roadmap.success_metrics,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting success metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
