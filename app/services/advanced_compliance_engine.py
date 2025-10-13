"""
Advanced Compliance Engine - Industry-Level Compliance Analysis
Provides comprehensive compliance analysis, ROI calculations, and regulatory readiness
"""
import logging
import json
import hashlib
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, text
import numpy as np
from scipy import stats
import uuid

from ..models import EmissionRecord, AuditSnapshot, ComplianceRule

logger = logging.getLogger(__name__)

@dataclass
class ComplianceGap:
    """Compliance gap analysis result"""
    gap_id: str
    framework: str
    requirement: str
    severity: str
    current_status: str
    gap_description: str
    affected_records: int
    estimated_cost: float
    estimated_time: int  # days
    priority_score: float
    remediation_actions: List[str]
    roi_impact: float

@dataclass
class ROIAnalysis:
    """ROI analysis for compliance investments"""
    total_investment: float
    compliance_cost_savings: float
    penalty_avoidance: float
    operational_efficiency: float
    reputation_value: float
    total_roi: float
    payback_period: int  # months
    risk_reduction: float
    competitive_advantage: float

@dataclass
class RegulatoryReadiness:
    """Regulatory framework readiness assessment"""
    framework: str
    readiness_score: float
    compliance_rate: float
    missing_requirements: List[str]
    critical_gaps: List[str]
    estimated_preparation_time: int  # days
    estimated_cost: float
    risk_level: str

class AdvancedComplianceEngine:
    """Advanced compliance analysis engine with industry-level features"""
    
    def __init__(self, db: Session):
        self.db = db
        self.regulatory_frameworks = self._load_regulatory_frameworks()
        self.compliance_costs = self._load_compliance_costs()
        
    def _load_regulatory_frameworks(self) -> Dict[str, Dict]:
        """Load regulatory framework requirements"""
        return {
            'EPA': {
                'name': 'Environmental Protection Agency (US)',
                'requirements': [
                    'emission_factor_source_verification',
                    'activity_data_completeness',
                    'calculation_methodology_documentation',
                    'uncertainty_quantification',
                    'third_party_verification',
                    'annual_reporting',
                    'record_retention_5_years'
                ],
                'penalties': {
                    'minor_violation': 50000,
                    'major_violation': 250000,
                    'repeat_violation': 500000
                },
                'deadlines': {
                    'annual_report': 'March 31',
                    'quarterly_updates': 'Last day of quarter'
                }
            },
            'EU_ETS': {
                'name': 'European Union Emissions Trading System',
                'requirements': [
                    'monitoring_plan_approval',
                    'verification_by_accredited_verifier',
                    'annual_emission_report',
                    'surrendering_allowances',
                    'registry_account_management',
                    'compliance_with_mrv_regulation'
                ],
                'penalties': {
                    'excess_emissions': 100,  # EUR per tonne
                    'late_surrender': 200,   # EUR per tonne
                    'non_compliance': 500000  # EUR
                },
                'deadlines': {
                    'annual_report': 'March 31',
                    'allowance_surrender': 'April 30'
                }
            },
            'TCFD': {
                'name': 'Task Force on Climate-related Financial Disclosures',
                'requirements': [
                    'governance_disclosure',
                    'strategy_disclosure',
                    'risk_management_disclosure',
                    'metrics_targets_disclosure',
                    'scenario_analysis',
                    'forward_looking_statements'
                ],
                'penalties': {
                    'investor_confidence_loss': 0.05,  # 5% of market cap
                    'regulatory_action': 1000000,
                    'reputation_damage': 0.02  # 2% of revenue
                },
                'deadlines': {
                    'annual_report': 'Annual',
                    'quarterly_updates': 'Quarterly'
                }
            },
            'SEC': {
                'name': 'Securities and Exchange Commission (US)',
                'requirements': [
                    'climate_risk_disclosure',
                    'emission_data_accuracy',
                    'governance_structure',
                    'risk_management_processes',
                    'material_impact_assessment',
                    'forward_looking_statements'
                ],
                'penalties': {
                    'material_misstatement': 5000000,
                    'inadequate_disclosure': 1000000,
                    'investor_harm': 0.1  # 10% of market cap
                },
                'deadlines': {
                    '10k_filing': '60-90 days after year end',
                    'quarterly_updates': '40-45 days after quarter end'
                }
            },
            'CARB': {
                'name': 'California Air Resources Board',
                'requirements': [
                    'mandatory_reporting',
                    'third_party_verification',
                    'emission_reduction_plan',
                    'compliance_offset_programs',
                    'annual_verification',
                    'record_keeping_requirements'
                ],
                'penalties': {
                    'reporting_violation': 10000,
                    'verification_failure': 25000,
                    'non_compliance': 100000
                },
                'deadlines': {
                    'annual_report': 'April 1',
                    'verification': 'June 1'
                }
            }
        }
    
    def _load_compliance_costs(self) -> Dict[str, float]:
        """Load typical compliance costs by activity"""
        return {
            'data_collection': 50,  # per record
            'verification': 200,    # per record
            'reporting': 1000,      # per report
            'audit_preparation': 5000,  # per audit
            'remediation': 100,     # per gap
            'training': 500,        # per person
            'system_implementation': 50000,  # one-time
            'ongoing_maintenance': 10000,    # annual
        }
    
    def analyze_compliance_gaps(self, framework: str, record_ids: Optional[List[str]] = None) -> List[ComplianceGap]:
        """
        Analyze compliance gaps for a specific regulatory framework
        
        Args:
            framework: Regulatory framework (EPA, EU_ETS, TCFD, SEC, CARB)
            record_ids: Optional list of specific record IDs to analyze
            
        Returns:
            List of ComplianceGap objects
        """
        try:
            if framework not in self.regulatory_frameworks:
                raise ValueError(f"Unsupported framework: {framework}")
            
            framework_config = self.regulatory_frameworks[framework]
            gaps = []
            
            # Get records to analyze
            query = self.db.query(EmissionRecord)
            if record_ids:
                query = query.filter(EmissionRecord.id.in_(record_ids))
            
            records = query.all()
            
            # Analyze each requirement
            for requirement in framework_config['requirements']:
                gap = self._analyze_requirement_gap(framework, requirement, records)
                if gap:
                    gaps.append(gap)
            
            # Sort by priority score
            gaps.sort(key=lambda x: x.priority_score, reverse=True)
            
            return gaps
            
        except Exception as e:
            logger.error(f"Error analyzing compliance gaps: {e}")
            return []
    
    def _analyze_requirement_gap(self, framework: str, requirement: str, records: List[EmissionRecord]) -> Optional[ComplianceGap]:
        """Analyze gap for a specific requirement"""
        try:
            affected_records = 0
            gap_description = ""
            remediation_actions = []
            severity = "medium"
            estimated_cost = 0
            estimated_time = 0
            
            if requirement == 'emission_factor_source_verification':
                # Check for missing or unverified emission factors
                for record in records:
                    if not record.ef_source or record.ef_source.lower() in ['unknown', 'estimated', 'default']:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records lack verified emission factor sources"
                    remediation_actions = [
                        "Implement emission factor verification process",
                        "Establish relationships with verified data providers",
                        "Create internal validation procedures"
                    ]
                    severity = "high"
                    estimated_cost = affected_records * 200  # verification cost per record
                    estimated_time = 30
            
            elif requirement == 'activity_data_completeness':
                # Check for missing required fields
                required_fields = ['supplier_name', 'date', 'activity_type', 'activity_amount', 'activity_unit']
                for record in records:
                    for field in required_fields:
                        if not getattr(record, field, None):
                            affected_records += 1
                            break
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records have incomplete activity data"
                    remediation_actions = [
                        "Implement data validation rules",
                        "Create data collection templates",
                        "Establish data quality monitoring"
                    ]
                    severity = "high"
                    estimated_cost = affected_records * 50  # data collection cost per record
                    estimated_time = 14
            
            elif requirement == 'calculation_methodology_documentation':
                # Check for missing methodology documentation
                for record in records:
                    if not record.methodology or record.methodology.lower() in ['unknown', 'default']:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records lack methodology documentation"
                    remediation_actions = [
                        "Document calculation methodologies",
                        "Create methodology templates",
                        "Implement methodology validation"
                    ]
                    severity = "medium"
                    estimated_cost = affected_records * 100  # documentation cost per record
                    estimated_time = 21
            
            elif requirement == 'uncertainty_quantification':
                # Check for missing uncertainty data
                for record in records:
                    if not record.uncertainty_pct or record.uncertainty_pct == 0:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records lack uncertainty quantification"
                    remediation_actions = [
                        "Implement uncertainty calculation methods",
                        "Train staff on uncertainty assessment",
                        "Create uncertainty reporting templates"
                    ]
                    severity = "medium"
                    estimated_cost = affected_records * 75  # uncertainty calculation cost per record
                    estimated_time = 14
            
            elif requirement == 'third_party_verification':
                # Check for missing verification (using data_quality_score as proxy)
                for record in records:
                    if not record.data_quality_score or record.data_quality_score < 80:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records require third-party verification"
                    remediation_actions = [
                        "Engage accredited verification body",
                        "Prepare verification documentation",
                        "Implement verification process"
                    ]
                    severity = "critical"
                    estimated_cost = affected_records * 300  # verification cost per record
                    estimated_time = 60
            
            # EU_ETS specific requirements
            elif requirement == 'monitoring_plan_approval':
                # Check if monitoring plan is approved (using compliance_score as proxy)
                for record in records:
                    if not record.compliance_score or record.compliance_score < 85:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records indicate monitoring plan needs approval"
                    remediation_actions = [
                        "Submit monitoring plan to competent authority",
                        "Address authority feedback",
                        "Obtain formal approval"
                    ]
                    severity = "critical"
                    estimated_cost = 50000  # monitoring plan development
                    estimated_time = 90
            
            elif requirement == 'verification_by_accredited_verifier':
                # Check for accredited verification
                for record in records:
                    if not record.data_quality_score or record.data_quality_score < 90:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records need accredited verification"
                    remediation_actions = [
                        "Engage EU-accredited verifier",
                        "Prepare verification documentation",
                        "Complete verification process"
                    ]
                    severity = "critical"
                    estimated_cost = affected_records * 500  # verification cost per record
                    estimated_time = 60
            
            elif requirement == 'annual_emission_report':
                # Check for annual reporting compliance
                for record in records:
                    if not record.audit_ready:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records not ready for annual emission report"
                    remediation_actions = [
                        "Prepare annual emission report",
                        "Validate all emission data",
                        "Submit to competent authority"
                    ]
                    severity = "high"
                    estimated_cost = 25000  # report preparation
                    estimated_time = 30
            
            elif requirement == 'surrendering_allowances':
                # Check for allowance surrender compliance
                for record in records:
                    if not record.compliance_score or record.compliance_score < 95:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records indicate allowance surrender issues"
                    remediation_actions = [
                        "Calculate required allowances",
                        "Purchase additional allowances if needed",
                        "Surrender allowances by deadline"
                    ]
                    severity = "critical"
                    estimated_cost = affected_records * 1000  # allowance cost per record
                    estimated_time = 15
            
            # TCFD specific requirements
            elif requirement == 'governance_disclosure':
                # Check for governance disclosure gaps
                for record in records:
                    if not record.supplier_name or record.supplier_name.lower() in ['unknown', 'n/a']:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records lack governance disclosure data"
                    remediation_actions = [
                        "Document governance structure",
                        "Define climate-related responsibilities",
                        "Create governance disclosure framework"
                    ]
                    severity = "high"
                    estimated_cost = 30000  # governance documentation
                    estimated_time = 45
            
            elif requirement == 'strategy_disclosure':
                # Check for strategy disclosure gaps
                for record in records:
                    if not record.activity_type or record.activity_type.lower() in ['unknown', 'other']:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records lack strategy disclosure data"
                    remediation_actions = [
                        "Develop climate strategy",
                        "Document strategic approach",
                        "Create strategy disclosure framework"
                    ]
                    severity = "high"
                    estimated_cost = 40000  # strategy development
                    estimated_time = 60
            
            elif requirement == 'risk_management_disclosure':
                # Check for risk management disclosure gaps
                for record in records:
                    if not record.uncertainty_pct or record.uncertainty_pct == 0:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records lack risk management data"
                    remediation_actions = [
                        "Implement risk management processes",
                        "Document risk assessment procedures",
                        "Create risk disclosure framework"
                    ]
                    severity = "high"
                    estimated_cost = 35000  # risk management setup
                    estimated_time = 45
            
            elif requirement == 'metrics_targets_disclosure':
                # Check for metrics and targets disclosure gaps
                for record in records:
                    if not record.emissions_kgco2e or record.emissions_kgco2e <= 0:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records lack metrics and targets data"
                    remediation_actions = [
                        "Define climate metrics and targets",
                        "Implement tracking systems",
                        "Create metrics disclosure framework"
                    ]
                    severity = "medium"
                    estimated_cost = 25000  # metrics setup
                    estimated_time = 30
            
            # SEC specific requirements
            elif requirement == 'climate_risk_disclosure':
                # Check for climate risk disclosure gaps
                for record in records:
                    if not record.compliance_score or record.compliance_score < 80:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records indicate climate risk disclosure gaps"
                    remediation_actions = [
                        "Conduct climate risk assessment",
                        "Document climate-related risks",
                        "Create risk disclosure framework"
                    ]
                    severity = "critical"
                    estimated_cost = 50000  # risk assessment
                    estimated_time = 90
            
            elif requirement == 'emission_data_accuracy':
                # Check for emission data accuracy gaps
                for record in records:
                    if not record.data_quality_score or record.data_quality_score < 85:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records have accuracy issues"
                    remediation_actions = [
                        "Implement data validation processes",
                        "Enhance data collection procedures",
                        "Create accuracy monitoring system"
                    ]
                    severity = "high"
                    estimated_cost = affected_records * 100  # accuracy improvement per record
                    estimated_time = 30
            
            elif requirement == 'governance_structure':
                # Check for governance structure gaps
                for record in records:
                    if not record.supplier_name or record.supplier_name.lower() in ['unknown', 'n/a']:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records lack governance structure data"
                    remediation_actions = [
                        "Define governance structure",
                        "Document roles and responsibilities",
                        "Create governance framework"
                    ]
                    severity = "high"
                    estimated_cost = 30000  # governance setup
                    estimated_time = 45
            
            # CARB specific requirements
            elif requirement == 'mandatory_reporting':
                # Check for mandatory reporting compliance
                for record in records:
                    if not record.audit_ready:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records not ready for mandatory reporting"
                    remediation_actions = [
                        "Prepare mandatory reporting documentation",
                        "Validate all required data",
                        "Submit to CARB"
                    ]
                    severity = "critical"
                    estimated_cost = 40000  # reporting preparation
                    estimated_time = 60
            
            elif requirement == 'emission_reduction_plan':
                # Check for emission reduction plan gaps
                for record in records:
                    if not record.compliance_score or record.compliance_score < 75:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records indicate emission reduction plan gaps"
                    remediation_actions = [
                        "Develop emission reduction plan",
                        "Set reduction targets",
                        "Implement reduction measures"
                    ]
                    severity = "high"
                    estimated_cost = 60000  # plan development
                    estimated_time = 120
            
            elif requirement == 'compliance_offset_programs':
                # Check for offset program compliance
                for record in records:
                    if not record.compliance_score or record.compliance_score < 90:
                        affected_records += 1
                
                if affected_records > 0:
                    gap_description = f"{affected_records} records indicate offset program compliance issues"
                    remediation_actions = [
                        "Evaluate offset program options",
                        "Purchase appropriate offsets",
                        "Document offset compliance"
                    ]
                    severity = "medium"
                    estimated_cost = affected_records * 200  # offset cost per record
                    estimated_time = 30
            
            # If no specific gap found, return None
            if affected_records == 0:
                return None
            
            # Calculate priority score
            priority_score = self._calculate_priority_score(affected_records, severity, framework)
            
            # Calculate ROI impact
            roi_impact = self._calculate_roi_impact(framework, requirement, affected_records, estimated_cost)
            
            if affected_records > 0:
                return ComplianceGap(
                    gap_id=f"{framework}_{requirement}_{uuid.uuid4().hex[:8]}",
                    framework=framework,
                    requirement=requirement,
                    severity=severity,
                    current_status="non_compliant",
                    gap_description=gap_description,
                    affected_records=affected_records,
                    estimated_cost=estimated_cost,
                    estimated_time=estimated_time,
                    priority_score=priority_score,
                    remediation_actions=remediation_actions,
                    roi_impact=roi_impact
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing requirement gap {requirement}: {e}")
            return None
    
    def _calculate_priority_score(self, affected_records: int, severity: str, framework: str) -> float:
        """Calculate priority score for a compliance gap"""
        severity_weights = {
            'critical': 1.0,
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }
        
        # Base score from severity
        base_score = severity_weights.get(severity, 0.5) * 100
        
        # Adjust for number of affected records
        record_factor = min(affected_records / 100, 1.0)  # Cap at 100 records
        record_adjustment = record_factor * 20
        
        # Framework-specific adjustments
        framework_penalties = {
            'EPA': 1.2,
            'EU_ETS': 1.3,
            'SEC': 1.4,
            'TCFD': 1.1,
            'CARB': 1.2
        }
        
        framework_multiplier = framework_penalties.get(framework, 1.0)
        
        return (base_score + record_adjustment) * framework_multiplier
    
    def _calculate_roi_impact(self, framework: str, requirement: str, affected_records: int, estimated_cost: float) -> float:
        """Calculate ROI impact of addressing a compliance gap"""
        framework_config = self.regulatory_frameworks[framework]
        
        # Calculate potential penalties avoided
        penalty_avoidance = 0
        if affected_records > 0:
            # Estimate penalty based on severity and number of records
            base_penalty = framework_config['penalties'].get('minor_violation', 10000)
            penalty_avoidance = base_penalty * (affected_records / 100)  # Scale with records
        
        # Calculate operational efficiency gains
        efficiency_gains = affected_records * 25  # $25 per record efficiency gain
        
        # Calculate total benefits
        total_benefits = penalty_avoidance + efficiency_gains
        
        # Calculate ROI
        if estimated_cost > 0:
            roi = ((total_benefits - estimated_cost) / estimated_cost) * 100
        else:
            roi = 0
        
        return roi
    
    def calculate_compliance_roi(self, framework: str, investment_amount: float, 
                               time_horizon_months: int = 12) -> ROIAnalysis:
        """
        Calculate ROI for compliance investments
        
        Args:
            framework: Regulatory framework
            investment_amount: Total investment amount
            time_horizon_months: Time horizon for ROI calculation
            
        Returns:
            ROIAnalysis object
        """
        try:
            framework_config = self.regulatory_frameworks[framework]
            
            # Calculate compliance cost savings
            current_records = self.db.query(EmissionRecord).count()
            annual_compliance_cost = current_records * 150  # $150 per record annually
            compliance_cost_savings = annual_compliance_cost * 0.3  # 30% savings from automation
            
            # Calculate penalty avoidance
            penalty_avoidance = 0
            for penalty_type, amount in framework_config['penalties'].items():
                if isinstance(amount, (int, float)):
                    penalty_avoidance += amount * 0.1  # 10% probability of penalty
                else:
                    # Percentage-based penalties (like market cap impact)
                    penalty_avoidance += 1000000  # Assume $1M base impact
            
            # Calculate operational efficiency gains
            operational_efficiency = current_records * 50  # $50 per record efficiency gain
            
            # Calculate reputation value
            reputation_value = 500000  # $500K annual reputation value
            
            # Calculate total benefits
            total_benefits = (
                compliance_cost_savings + 
                penalty_avoidance + 
                operational_efficiency + 
                reputation_value
            )
            
            # Calculate ROI
            total_roi = ((total_benefits - investment_amount) / investment_amount) * 100
            
            # Calculate payback period
            monthly_benefits = total_benefits / 12
            if monthly_benefits > 0:
                payback_period = int(investment_amount / monthly_benefits)
            else:
                payback_period = 999
            
            # Calculate risk reduction
            risk_reduction = min(penalty_avoidance / 1000000, 1.0) * 100  # Max 100% risk reduction
            
            # Calculate competitive advantage
            competitive_advantage = reputation_value * 0.5  # 50% of reputation value
            
            return ROIAnalysis(
                total_investment=investment_amount,
                compliance_cost_savings=compliance_cost_savings,
                penalty_avoidance=penalty_avoidance,
                operational_efficiency=operational_efficiency,
                reputation_value=reputation_value,
                total_roi=total_roi,
                payback_period=payback_period,
                risk_reduction=risk_reduction,
                competitive_advantage=competitive_advantage
            )
            
        except Exception as e:
            logger.error(f"Error calculating compliance ROI: {e}")
            return ROIAnalysis(
                total_investment=investment_amount,
                compliance_cost_savings=0,
                penalty_avoidance=0,
                operational_efficiency=0,
                reputation_value=0,
                total_roi=0,
                payback_period=999,
                risk_reduction=0,
                competitive_advantage=0
            )
    
    def assess_regulatory_readiness(self, framework: str) -> RegulatoryReadiness:
        """
        Assess readiness for a specific regulatory framework
        
        Args:
            framework: Regulatory framework to assess
            
        Returns:
            RegulatoryReadiness object
        """
        try:
            if framework not in self.regulatory_frameworks:
                raise ValueError(f"Unsupported framework: {framework}")
            
            framework_config = self.regulatory_frameworks[framework]
            
            # Get all records
            total_records = self.db.query(EmissionRecord).count()
            
            # Analyze compliance gaps
            gaps = self.analyze_compliance_gaps(framework)
            
            # Calculate compliance rate based on actual audit snapshot data
            # Use the enhanced audit snapshot compliance score as the base
            from ..models_enhanced_audit import EnhancedAuditSnapshot
            audit_snapshots = self.db.query(EnhancedAuditSnapshot).filter(
                EnhancedAuditSnapshot.submission_type == framework.upper()
            ).order_by(EnhancedAuditSnapshot.submission_date.desc()).limit(1).all()
            
            if audit_snapshots:
                # Use the most recent audit snapshot compliance score
                base_compliance_rate = float(audit_snapshots[0].average_compliance_score or 0)
            else:
                # Fallback: calculate based on gaps (but don't go negative)
                base_compliance_rate = 100.0
                for gap in gaps:
                    # Reduce compliance rate based on gap severity
                    if gap.severity == 'critical':
                        base_compliance_rate -= 15  # -15% per critical gap
                    elif gap.severity == 'high':
                        base_compliance_rate -= 10  # -10% per high gap
                    elif gap.severity == 'medium':
                        base_compliance_rate -= 5   # -5% per medium gap
                    else:
                        base_compliance_rate -= 2   # -2% per low gap
            
            compliance_rate = max(0, min(100, base_compliance_rate))
            
            # Calculate readiness score based on compliance rate and gaps
            readiness_score = compliance_rate
            
            # Adjust for critical gaps (but don't go below 0)
            critical_gaps = [gap for gap in gaps if gap.severity == 'critical']
            if critical_gaps:
                readiness_score -= min(len(critical_gaps) * 5, readiness_score)  # -5 points per critical gap, but don't go negative
            
            # Adjust for high severity gaps
            high_gaps = [gap for gap in gaps if gap.severity == 'high']
            if high_gaps:
                readiness_score -= min(len(high_gaps) * 3, readiness_score)  # -3 points per high gap, but don't go negative
            
            readiness_score = max(0, min(100, readiness_score))
            
            # Collect missing requirements
            missing_requirements = [gap.requirement for gap in gaps]
            
            # Collect critical gaps
            critical_gap_descriptions = [gap.gap_description for gap in critical_gaps]
            
            # Estimate preparation time
            estimated_preparation_time = sum(gap.estimated_time for gap in gaps)
            
            # Estimate cost
            estimated_cost = sum(gap.estimated_cost for gap in gaps)
            
            # Determine risk level
            if readiness_score >= 90:
                risk_level = "low"
            elif readiness_score >= 70:
                risk_level = "medium"
            elif readiness_score >= 50:
                risk_level = "high"
            else:
                risk_level = "critical"
            
            return RegulatoryReadiness(
                framework=framework,
                readiness_score=readiness_score,
                compliance_rate=compliance_rate,
                missing_requirements=missing_requirements,
                critical_gaps=critical_gap_descriptions,
                estimated_preparation_time=estimated_preparation_time,
                estimated_cost=estimated_cost,
                risk_level=risk_level
            )
            
        except Exception as e:
            logger.error(f"Error assessing regulatory readiness: {e}")
            return RegulatoryReadiness(
                framework=framework,
                readiness_score=0,
                compliance_rate=0,
                missing_requirements=[],
                critical_gaps=[],
                estimated_preparation_time=0,
                estimated_cost=0,
                risk_level="critical"
            )
    
    def generate_compliance_roadmap(self, frameworks: List[str], 
                                  budget_constraint: float = 100000) -> Dict[str, Any]:
        """
        Generate a compliance roadmap for multiple frameworks
        
        Args:
            frameworks: List of regulatory frameworks
            budget_constraint: Budget constraint for compliance investments
            
        Returns:
            Dictionary with compliance roadmap
        """
        try:
            roadmap = {
                'total_budget': budget_constraint,
                'allocated_budget': 0,
                'remaining_budget': budget_constraint,
                'frameworks': {},
                'priority_actions': [],
                'timeline': [],
                'expected_roi': 0
            }
            
            # Assess readiness for each framework
            framework_assessments = {}
            for framework in frameworks:
                assessment = self.assess_regulatory_readiness(framework)
                framework_assessments[framework] = assessment
                roadmap['frameworks'][framework] = {
                    'readiness_score': assessment.readiness_score,
                    'compliance_rate': assessment.compliance_rate,
                    'estimated_cost': assessment.estimated_cost,
                    'estimated_time': assessment.estimated_preparation_time,
                    'risk_level': assessment.risk_level,
                    'critical_gaps': assessment.critical_gaps
                }
            
            # Prioritize frameworks by risk and cost
            framework_priorities = []
            for framework, assessment in framework_assessments.items():
                priority_score = 0
                
                # Risk-based priority
                risk_weights = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
                priority_score += risk_weights.get(assessment.risk_level, 1) * 25
                
                # Cost efficiency (lower cost = higher priority)
                if assessment.estimated_cost > 0:
                    cost_efficiency = 100 / (assessment.estimated_cost / 10000)  # Normalize cost
                    priority_score += min(cost_efficiency, 25)
                
                # Compliance rate (lower compliance = higher priority)
                priority_score += (100 - assessment.compliance_rate) * 0.5
                
                framework_priorities.append((framework, priority_score, assessment))
            
            # Sort by priority
            framework_priorities.sort(key=lambda x: x[1], reverse=True)
            
            # Allocate budget
            for framework, priority_score, assessment in framework_priorities:
                if roadmap['remaining_budget'] <= 0:
                    break
                
                # Allocate budget for this framework
                allocation = min(assessment.estimated_cost, roadmap['remaining_budget'])
                roadmap['allocated_budget'] += allocation
                roadmap['remaining_budget'] -= allocation
                
                # Add to priority actions
                roadmap['priority_actions'].append({
                    'framework': framework,
                    'action': f"Address {len(assessment.critical_gaps)} critical gaps",
                    'cost': allocation,
                    'time': assessment.estimated_preparation_time,
                    'priority_score': priority_score
                })
            
            # Generate timeline
            current_date = datetime.now()
            for action in roadmap['priority_actions']:
                start_date = current_date
                end_date = start_date + timedelta(days=action['time'])
                
                roadmap['timeline'].append({
                    'framework': action['framework'],
                    'action': action['action'],
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'duration_days': action['time']
                })
                
                current_date = end_date
            
            # Calculate expected ROI
            total_roi = 0
            for framework in frameworks:
                roi_analysis = self.calculate_compliance_roi(framework, roadmap['frameworks'][framework]['estimated_cost'])
                total_roi += roi_analysis.total_roi
            
            roadmap['expected_roi'] = total_roi / len(frameworks) if frameworks else 0
            
            return roadmap
            
        except Exception as e:
            logger.error(f"Error generating compliance roadmap: {e}")
            return {
                'error': str(e),
                'total_budget': budget_constraint,
                'allocated_budget': 0,
                'remaining_budget': budget_constraint,
                'frameworks': {},
                'priority_actions': [],
                'timeline': [],
                'expected_roi': 0
            }
    
    def get_compliance_benchmark(self, industry: str = "manufacturing") -> Dict[str, Any]:
        """
        Get compliance benchmarking data for industry comparison
        
        Args:
            industry: Industry sector for benchmarking
            
        Returns:
            Dictionary with benchmark data
        """
        try:
            # Industry-specific benchmarks (mock data - in real implementation, this would come from industry databases)
            industry_benchmarks = {
                'manufacturing': {
                    'average_compliance_score': 78.5,
                    'average_compliance_cost_per_record': 125,
                    'average_verification_rate': 85.2,
                    'average_penalty_frequency': 0.15,  # 15% of companies face penalties
                    'average_roi': 245.3
                },
                'energy': {
                    'average_compliance_score': 82.1,
                    'average_compliance_cost_per_record': 180,
                    'average_verification_rate': 92.5,
                    'average_penalty_frequency': 0.08,
                    'average_roi': 312.7
                },
                'transportation': {
                    'average_compliance_score': 71.3,
                    'average_compliance_cost_per_record': 95,
                    'average_verification_rate': 78.9,
                    'average_penalty_frequency': 0.22,
                    'average_roi': 198.4
                },
                'technology': {
                    'average_compliance_score': 88.7,
                    'average_compliance_cost_per_record': 200,
                    'average_verification_rate': 95.1,
                    'average_penalty_frequency': 0.05,
                    'average_roi': 456.2
                }
            }
            
            benchmark = industry_benchmarks.get(industry, industry_benchmarks['manufacturing'])
            
            # Get current company metrics
            total_records = self.db.query(EmissionRecord).count()
            avg_compliance_score = self.db.query(func.avg(EmissionRecord.compliance_score)).scalar() or 0
            verification_rate = (self.db.query(EmissionRecord).filter(EmissionRecord.verified == True).count() / total_records * 100) if total_records > 0 else 0
            
            # Calculate company performance vs benchmark
            performance_vs_benchmark = {
                'compliance_score': {
                    'company': avg_compliance_score,
                    'industry_average': benchmark['average_compliance_score'],
                    'performance': 'above' if avg_compliance_score > benchmark['average_compliance_score'] else 'below',
                    'gap': avg_compliance_score - benchmark['average_compliance_score']
                },
                'verification_rate': {
                    'company': verification_rate,
                    'industry_average': benchmark['average_verification_rate'],
                    'performance': 'above' if verification_rate > benchmark['average_verification_rate'] else 'below',
                    'gap': verification_rate - benchmark['average_verification_rate']
                }
            }
            
            return {
                'industry': industry,
                'benchmark_data': benchmark,
                'company_performance': performance_vs_benchmark,
                'recommendations': self._generate_benchmark_recommendations(performance_vs_benchmark, benchmark),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting compliance benchmark: {e}")
            return {
                'error': str(e),
                'industry': industry,
                'benchmark_data': {},
                'company_performance': {},
                'recommendations': [],
                'last_updated': datetime.now().isoformat()
            }
    
    def _generate_benchmark_recommendations(self, performance: Dict, benchmark: Dict) -> List[str]:
        """Generate recommendations based on benchmark comparison"""
        recommendations = []
        
        # Compliance score recommendations
        if performance['compliance_score']['performance'] == 'below':
            gap = performance['compliance_score']['gap']
            if gap < -10:
                recommendations.append("CRITICAL: Compliance score significantly below industry average. Immediate action required.")
            elif gap < -5:
                recommendations.append("HIGH PRIORITY: Improve compliance score to meet industry standards.")
            else:
                recommendations.append("MEDIUM PRIORITY: Minor improvements needed to reach industry average.")
        
        # Verification rate recommendations
        if performance['verification_rate']['performance'] == 'below':
            gap = performance['verification_rate']['gap']
            if gap < -15:
                recommendations.append("CRITICAL: Verification rate significantly below industry average. Implement verification program.")
            elif gap < -5:
                recommendations.append("HIGH PRIORITY: Increase verification rate to industry standards.")
            else:
                recommendations.append("MEDIUM PRIORITY: Minor improvements needed for verification rate.")
        
        # General recommendations
        if not recommendations:
            recommendations.append("EXCELLENT: Performance meets or exceeds industry benchmarks.")
        
        recommendations.append(f"Industry average ROI is {benchmark['average_roi']:.1f}%. Focus on high-ROI compliance investments.")
        recommendations.append(f"Industry penalty frequency is {benchmark['average_penalty_frequency']*100:.1f}%. Ensure robust compliance to avoid penalties.")
        
        return recommendations
