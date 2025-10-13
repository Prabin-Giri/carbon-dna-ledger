"""
Compliance Integrity Engine
Ensures audit readiness, regulatory trust, and data transparency
"""
import logging
import hashlib
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
import os
import uuid

from ..models import EmissionRecord, AuditSnapshot, ComplianceRule

logger = logging.getLogger(__name__)

@dataclass
class ComplianceScore:
    """Compliance score breakdown"""
    overall_score: float  # 0-100
    factor_source_quality: float  # 0-100
    metadata_completeness: float  # 0-100
    data_entry_method_score: float  # 0-100
    fingerprint_integrity: float  # 0-100
    llm_confidence: float  # 0-100
    compliance_flags: List[str]
    audit_ready: bool

@dataclass
class AuditSnapshotData:
    """Audit snapshot data structure"""
    submission_id: str
    submission_type: str
    reporting_period_start: date
    reporting_period_end: date
    merkle_root_hash: str
    total_records: int
    total_emissions_kgco2e: Decimal
    average_compliance_score: float
    audit_ready_records: int
    non_compliant_records: int
    compliance_flags: List[str]
    pdf_report_path: Optional[str] = None
    json_data_path: Optional[str] = None

class ComplianceIntegrityEngine:
    """Main service for compliance integrity and audit readiness"""
    
    def __init__(self, db: Session):
        self.db = db
        self.compliance_rules = self._load_compliance_rules()
        
        # Compliance scoring weights
        self.scoring_weights = {
            'factor_source_quality': 0.25,
            'metadata_completeness': 0.20,
            'data_entry_method_score': 0.20,
            'fingerprint_integrity': 0.20,
            'llm_confidence': 0.15
        }
    
    def calculate_compliance_score(self, record: Dict[str, Any]) -> ComplianceScore:
        """
        Calculate comprehensive compliance score for an emission record
        
        Args:
            record: Emission record dictionary
            
        Returns:
            ComplianceScore object with detailed breakdown
        """
        try:
            # Calculate individual component scores
            factor_source_quality = self._calculate_factor_source_quality(record)
            metadata_completeness = self._calculate_metadata_completeness(record)
            data_entry_method_score = self._calculate_data_entry_method_score(record)
            fingerprint_integrity = self._calculate_fingerprint_integrity(record)
            llm_confidence = self._calculate_llm_confidence(record)
            
            # Calculate weighted overall score
            overall_score = (
                factor_source_quality * self.scoring_weights['factor_source_quality'] +
                metadata_completeness * self.scoring_weights['metadata_completeness'] +
                data_entry_method_score * self.scoring_weights['data_entry_method_score'] +
                fingerprint_integrity * self.scoring_weights['fingerprint_integrity'] +
                llm_confidence * self.scoring_weights['llm_confidence']
            )
            
            # Apply compliance rules
            rule_violations = self.apply_compliance_rules(record)
            
            # Generate compliance flags
            compliance_flags = self._generate_compliance_flags(
                record, factor_source_quality, metadata_completeness,
                data_entry_method_score, fingerprint_integrity, llm_confidence
            )
            
            # Add rule violations to compliance flags
            compliance_flags.extend(rule_violations)
            
            # Determine audit readiness
            audit_ready = (
                overall_score >= 80 and
                len(compliance_flags) == 0 and
                fingerprint_integrity >= 90 and
                len(rule_violations) == 0
            )
            
            return ComplianceScore(
                overall_score=round(overall_score, 2),
                factor_source_quality=round(factor_source_quality, 2),
                metadata_completeness=round(metadata_completeness, 2),
                data_entry_method_score=round(data_entry_method_score, 2),
                fingerprint_integrity=round(fingerprint_integrity, 2),
                llm_confidence=round(llm_confidence, 2),
                compliance_flags=compliance_flags,
                audit_ready=audit_ready
            )
            
        except Exception as e:
            logger.error(f"Error calculating compliance score: {e}")
            return ComplianceScore(
                overall_score=0.0,
                factor_source_quality=0.0,
                metadata_completeness=0.0,
                data_entry_method_score=0.0,
                fingerprint_integrity=0.0,
                llm_confidence=0.0,
                compliance_flags=[f"Error calculating score: {str(e)}"],
                audit_ready=False
            )
    
    def _calculate_factor_source_quality(self, record: Dict[str, Any]) -> float:
        """Calculate emission factor source quality score"""
        # Use methodology field as the primary indicator
        methodology = (record.get('methodology') or '').lower()
        data_quality_score = record.get('data_quality_score', 0)
        
        score = 0.0
        
        # Methodology quality scoring
        if 'activity-based' in methodology:
            score += 50  # Highest quality - activity-based
        elif 'spend-based' in methodology:
            score += 40  # Good quality - spend-based
        elif 'hybrid' in methodology:
            score += 45  # Very good - hybrid approach
        elif methodology:
            score += 20  # Any methodology is better than none
        
        # Data quality score contribution (scale 0-10 to 0-30)
        if data_quality_score:
            score += min(data_quality_score * 3, 30)  # Max 30 points from data quality
        
        # Additional quality indicators
        if record.get('emissions_kgco2e', 0) > 0:
            score += 10  # Has actual emissions data
        
        return min(score, 100.0)  # Cap at 100
    
    def _calculate_metadata_completeness(self, record: Dict[str, Any]) -> float:
        """Calculate metadata completeness score"""
        required_fields = [
            'supplier_name', 'date', 'scope', 'emissions_kgco2e',
            'methodology', 'category', 'data_quality_score'
        ]
        
        optional_fields = [
            'activity_type', 'activity_amount', 'activity_unit',
            'date_start', 'date_end', 'created_at'
        ]
        
        score = 0.0
        
        # Required fields (70% of score)
        required_present = sum(1 for field in required_fields if record.get(field) is not None)
        required_score = (required_present / len(required_fields)) * 70
        score += required_score
        
        # Optional fields (30% of score)
        optional_present = sum(1 for field in optional_fields if record.get(field) is not None)
        optional_score = (optional_present / len(optional_fields)) * 30
        score += optional_score
        
        return min(100.0, score)
    
    def _calculate_data_entry_method_score(self, record: Dict[str, Any]) -> float:
        """Calculate score based on data entry method"""
        ai_classified = record.get('ai_classified', False)
        needs_human_review = record.get('needs_human_review', False)
        confidence_score = float(record.get('confidence_score', 0))
        
        # Handle both boolean and string values
        if isinstance(ai_classified, str):
            ai_classified = ai_classified.lower() == 'true'
        if isinstance(needs_human_review, str):
            needs_human_review = needs_human_review.lower() == 'true'
        
        if ai_classified:
            if not needs_human_review and confidence_score >= 0.8:
                return 90.0  # High-confidence AI classification
            elif not needs_human_review and confidence_score >= 0.6:
                return 75.0  # Medium-confidence AI classification
            else:
                return 60.0  # AI classification requiring review
        else:
            return 85.0  # Manual entry (assumed to be reviewed)
    
    def _calculate_fingerprint_integrity(self, record: Dict[str, Any]) -> float:
        """Calculate fingerprint integrity score"""
        record_hash = record.get('record_hash')
        previous_hash = record.get('previous_hash')
        salt = record.get('salt')
        
        score = 0.0
        
        if record_hash:
            score += 40  # Hash present
        if previous_hash:
            score += 30  # Chain integrity
        if salt:
            score += 20  # Salt for uniqueness
        if len(record_hash or '') == 64:  # SHA-256 length
            score += 10  # Proper hash length
        
        return min(100.0, score)
    
    def _calculate_llm_confidence(self, record: Dict[str, Any]) -> float:
        """Calculate LLM confidence score"""
        ai_classified = record.get('ai_classified', False)
        confidence_score = float(record.get('confidence_score', 0))
        
        # Handle both boolean and string values
        if isinstance(ai_classified, str):
            ai_classified = ai_classified.lower() == 'true'
        
        if ai_classified:
            return confidence_score * 100  # Convert 0-1 to 0-100
        else:
            return 100.0  # Manual entry gets full confidence
    
    def _generate_compliance_flags(self, record: Dict[str, Any], 
                                 factor_score: float, metadata_score: float,
                                 method_score: float, fingerprint_score: float,
                                 llm_score: float) -> List[str]:
        """Generate compliance flags based on scores"""
        flags = []
        
        if factor_score < 50:
            flags.append("Low emission factor source quality")
        if metadata_score < 70:
            flags.append("Incomplete metadata")
        if method_score < 60:
            flags.append("Data entry method concerns")
        if fingerprint_score < 80:
            flags.append("Fingerprint integrity issues")
        if llm_score < 70:
            flags.append("Low AI confidence")
        
        # Additional compliance checks
        if not record.get('record_hash'):
            flags.append("Missing record hash")
        if not record.get('supplier_name'):
            flags.append("Missing supplier information")
        if not record.get('date'):
            flags.append("Missing date information")
        if record.get('emissions_kgco2e') is None or record.get('emissions_kgco2e') <= 0:
            flags.append("Invalid or missing emission calculation")
        
        return flags
    
    def create_audit_snapshot(self, submission_type: str, 
                            reporting_period_start: date,
                            reporting_period_end: date,
                            record_ids: Optional[List[str]] = None,
                            allow_empty: bool = False) -> AuditSnapshotData:
        """
        Create an audit snapshot for regulatory submission
        
        Args:
            submission_type: Type of submission ('EPA', 'EU_ETS', 'CARB', etc.)
            reporting_period_start: Start date of reporting period
            reporting_period_end: End date of reporting period
            record_ids: Optional list of specific record IDs to include
            
        Returns:
            AuditSnapshotData object
        """
        try:
            # Generate unique submission ID
            submission_id = f"{submission_type}_{reporting_period_start.strftime('%Y%m%d')}_{reporting_period_end.strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
            
            # Get records for the period
            query = self.db.query(EmissionRecord).filter(
                and_(
                    EmissionRecord.date >= reporting_period_start,
                    EmissionRecord.date <= reporting_period_end
                )
            )
            
            if record_ids:
                query = query.filter(EmissionRecord.id.in_(record_ids))
            
            records = query.all()
            
            if not records:
                if not allow_empty:
                    raise ValueError("No records found for the specified period")
                # Proceed with empty snapshot (zeros) for audit trace
                total_records = 0
                total_emissions = 0.0
                average_compliance_score = 0.0
                audit_ready_records = 0
                non_compliant_records = 0
                merkle_root_hash = ""
                compliance_flags = []
                
                audit_snapshot = AuditSnapshot(
                    submission_id=f"{submission_type}_{reporting_period_start.strftime('%Y%m%d')}_{reporting_period_end.strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
                    submission_type=submission_type,
                    reporting_period_start=reporting_period_start,
                    reporting_period_end=reporting_period_end,
                    submission_date=datetime.now(),
                    merkle_root_hash=merkle_root_hash,
                    total_records=total_records,
                    total_emissions_kgco2e=Decimal(str(total_emissions)),
                    average_compliance_score=Decimal(str(average_compliance_score)),
                    audit_ready_records=audit_ready_records,
                    non_compliant_records=non_compliant_records,
                    compliance_flags=compliance_flags
                )
                self.db.add(audit_snapshot)
                self.db.commit()
                return AuditSnapshotData(
                    submission_id=audit_snapshot.submission_id,
                    submission_type=submission_type,
                    reporting_period_start=reporting_period_start,
                    reporting_period_end=reporting_period_end,
                    merkle_root_hash=merkle_root_hash,
                    total_records=total_records,
                    total_emissions_kgco2e=Decimal(str(total_emissions)),
                    average_compliance_score=average_compliance_score,
                    audit_ready_records=audit_ready_records,
                    non_compliant_records=non_compliant_records,
                    compliance_flags=compliance_flags
                )
            
            # Calculate totals and metrics
            total_records = len(records)
            total_emissions = sum(float(r.emissions_kgco2e or 0) for r in records)
            
            # Calculate compliance scores for each record
            compliance_scores = []
            audit_ready_count = 0
            all_compliance_flags = []
            
            for record in records:
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
                compliance_score = self.calculate_compliance_score(record_dict)
                compliance_scores.append(compliance_score.overall_score)
                
                if compliance_score.audit_ready:
                    audit_ready_count += 1
                
                all_compliance_flags.extend(compliance_score.compliance_flags)
            
            average_compliance_score = sum(compliance_scores) / total_records if total_records > 0 else 0
            audit_ready_records = audit_ready_count
            non_compliant_records = sum(1 for score in compliance_scores if score < 70)
            
            # Generate Merkle root hash
            merkle_root_hash = self._generate_merkle_root(records)
            
            # Use the compliance flags we already collected
            compliance_flags = list(set(all_compliance_flags))  # Remove duplicates
            
            # Create audit snapshot record
            audit_snapshot = AuditSnapshot(
                submission_id=submission_id,
                submission_type=submission_type,
                reporting_period_start=reporting_period_start,
                reporting_period_end=reporting_period_end,
                submission_date=datetime.now(),
                merkle_root_hash=merkle_root_hash,
                total_records=total_records,
                total_emissions_kgco2e=Decimal(str(total_emissions)),
                average_compliance_score=Decimal(str(average_compliance_score)),
                audit_ready_records=audit_ready_records,
                non_compliant_records=non_compliant_records,
                compliance_flags=compliance_flags
            )
            
            self.db.add(audit_snapshot)
            self.db.commit()
            
            return AuditSnapshotData(
                submission_id=submission_id,
                submission_type=submission_type,
                reporting_period_start=reporting_period_start,
                reporting_period_end=reporting_period_end,
                merkle_root_hash=merkle_root_hash,
                total_records=total_records,
                total_emissions_kgco2e=Decimal(str(total_emissions)),
                average_compliance_score=average_compliance_score,
                audit_ready_records=audit_ready_records,
                non_compliant_records=non_compliant_records,
                compliance_flags=compliance_flags
            )
            
        except Exception as e:
            logger.error(f"Error creating audit snapshot: {e}")
            self.db.rollback()
            raise
    
    def _generate_merkle_root(self, records: List[EmissionRecord]) -> str:
        """Generate Merkle root hash for a list of records"""
        if not records:
            return ""
        
        # Sort records by ID for consistent ordering
        sorted_records = sorted(records, key=lambda r: str(r.id))
        
        # Create leaf hashes
        leaf_hashes = []
        for record in sorted_records:
            # Create hash of record data
            record_data = {
                'id': str(record.id),
                'date': record.date.isoformat() if record.date else '',
                'supplier_name': record.supplier_name or '',
                'activity_type': record.activity_type or '',
                'emissions_kgco2e': str(record.emissions_kgco2e or 0),
                'record_hash': record.record_hash or ''
            }
            record_json = json.dumps(record_data, sort_keys=True)
            leaf_hash = hashlib.sha256(record_json.encode()).hexdigest()
            leaf_hashes.append(leaf_hash)
        
        # Build Merkle tree
        current_level = leaf_hashes
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(parent_hash)
            current_level = next_level
        
        return current_level[0] if current_level else ""
    
    def generate_compliance_report(self, snapshot_id: str) -> Dict[str, Any]:
        """Generate compliance report for an audit snapshot"""
        try:
            snapshot = self.db.query(AuditSnapshot).filter(
                AuditSnapshot.submission_id == snapshot_id
            ).first()
            
            if not snapshot:
                raise ValueError(f"Audit snapshot {snapshot_id} not found")
            
            # Get records for the snapshot period
            records = self.db.query(EmissionRecord).filter(
                and_(
                    EmissionRecord.date >= snapshot.reporting_period_start,
                    EmissionRecord.date <= snapshot.reporting_period_end
                )
            ).all()
            
            # Generate report data
            report_data = {
                'snapshot_id': snapshot.submission_id,
                'submission_type': snapshot.submission_type,
                'reporting_period': {
                    'start': snapshot.reporting_period_start.isoformat(),
                    'end': snapshot.reporting_period_end.isoformat()
                },
                'submission_date': snapshot.submission_date.isoformat(),
                'integrity': {
                    'merkle_root_hash': snapshot.merkle_root_hash,
                    'total_records': snapshot.total_records,
                    'total_emissions_kgco2e': float(snapshot.total_emissions_kgco2e)
                },
                'compliance_metrics': {
                    'average_compliance_score': float(snapshot.average_compliance_score),
                    'audit_ready_records': snapshot.audit_ready_records,
                    'non_compliant_records': snapshot.non_compliant_records,
                    'compliance_rate': (snapshot.audit_ready_records / snapshot.total_records * 100) if snapshot.total_records > 0 else 0
                },
                'compliance_flags': snapshot.compliance_flags,
                'records_summary': self._generate_records_summary(records),
                'regulatory_status': self._determine_regulatory_status(snapshot)
            }
            
            return report_data
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            raise
    
    def _generate_records_summary(self, records: List[EmissionRecord]) -> Dict[str, Any]:
        """Generate summary of records for compliance report"""
        if not records:
            return {}
        
        # Group by compliance score ranges
        score_ranges = {
            'excellent': sum(1 for r in records if r.compliance_score and r.compliance_score >= 90),
            'good': sum(1 for r in records if r.compliance_score and 80 <= r.compliance_score < 90),
            'fair': sum(1 for r in records if r.compliance_score and 70 <= r.compliance_score < 80),
            'poor': sum(1 for r in records if r.compliance_score and r.compliance_score < 70)
        }
        
        # Group by scope
        scope_breakdown = {}
        for record in records:
            scope = record.scope or 'unknown'
            if scope not in scope_breakdown:
                scope_breakdown[scope] = 0
            scope_breakdown[scope] += 1
        
        # Group by activity type
        activity_breakdown = {}
        for record in records:
            activity = record.activity_type or 'unknown'
            if activity not in activity_breakdown:
                activity_breakdown[activity] = 0
            activity_breakdown[activity] += 1
        
        return {
            'total_records': len(records),
            'compliance_score_ranges': score_ranges,
            'scope_breakdown': scope_breakdown,
            'activity_breakdown': activity_breakdown,
            'audit_ready_count': sum(1 for r in records if r.audit_ready)
        }
    
    def _determine_regulatory_status(self, snapshot: AuditSnapshot) -> str:
        """Determine regulatory compliance status"""
        compliance_rate = (snapshot.audit_ready_records / snapshot.total_records * 100) if snapshot.total_records > 0 else 0
        
        if compliance_rate >= 95 and snapshot.average_compliance_score >= 90:
            return 'excellent'
        elif compliance_rate >= 85 and snapshot.average_compliance_score >= 80:
            return 'good'
        elif compliance_rate >= 70 and snapshot.average_compliance_score >= 70:
            return 'fair'
        else:
            return 'poor'
    
    def _load_compliance_rules(self) -> List[ComplianceRule]:
        """Load compliance rules from database"""
        try:
            return self.db.query(ComplianceRule).filter(
                ComplianceRule.is_active == True
            ).all()
        except Exception as e:
            logger.error(f"Error loading compliance rules: {e}")
            return []
    
    def apply_compliance_rules(self, record: Dict[str, Any]) -> List[str]:
        """Apply compliance rules to a record and return violations"""
        violations = []
        
        for rule in self.compliance_rules:
            try:
                if self._rule_matches(rule, record):
                    violations.extend(self._check_rule_requirements(rule, record))
            except Exception as e:
                logger.error(f"Error applying rule {rule.rule_id}: {e}")
        
        return violations
    
    def _rule_matches(self, rule: ComplianceRule, record: Dict[str, Any]) -> bool:
        """Check if a rule matches the record"""
        conditions = rule.conditions
        
        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            record_value = record.get(field)
            
            if not self._evaluate_condition(record_value, operator, value):
                return False
        
        return True
    
    def _evaluate_condition(self, record_value: Any, operator: str, expected_value: Any) -> bool:
        """Evaluate a single condition"""
        if operator == 'equals':
            return record_value == expected_value
        elif operator == 'not_equals':
            return record_value != expected_value
        elif operator == 'greater_than':
            return float(record_value or 0) > float(expected_value)
        elif operator == 'less_than':
            return float(record_value or 0) < float(expected_value)
        elif operator == 'contains':
            return expected_value in (record_value or '')
        elif operator == 'not_null':
            return record_value is not None
        elif operator == 'is_null':
            return record_value is None
        else:
            return False
    
    def _check_rule_requirements(self, rule: ComplianceRule, record: Dict[str, Any]) -> List[str]:
        """Check if record meets rule requirements"""
        violations = []
        
        # Check required fields
        for field in rule.required_fields:
            if not record.get(field):
                violations.append(f"Missing required field: {field}")
        
        # Check validation rules
        for validation in rule.validation_rules:
            field = validation.get('field')
            rule_type = validation.get('type')
            value = validation.get('value')
            
            record_value = record.get(field)
            
            if rule_type == 'min_length' and len(str(record_value or '')) < value:
                violations.append(f"Field {field} too short (minimum {value} characters)")
            elif rule_type == 'max_length' and len(str(record_value or '')) > value:
                violations.append(f"Field {field} too long (maximum {value} characters)")
            elif rule_type == 'min_value' and float(record_value or 0) < value:
                violations.append(f"Field {field} below minimum value ({value})")
            elif rule_type == 'max_value' and float(record_value or 0) > value:
                violations.append(f"Field {field} above maximum value ({value})")
        
        return violations
    
    def get_compliance_dashboard_data(self) -> Dict[str, Any]:
        """Get data for compliance dashboard"""
        try:
            # Get recent records
            recent_records = self.db.query(EmissionRecord).filter(
                EmissionRecord.created_at >= datetime.now() - timedelta(days=30)
            ).all()
            
            # Calculate overall metrics
            total_records = len(recent_records)
            audit_ready_count = sum(1 for r in recent_records if r.audit_ready)
            average_compliance_score = sum(float(r.compliance_score or 0) for r in recent_records) / total_records if total_records > 0 else 0
            
            # Get compliance score distribution
            score_distribution = {
                'excellent': sum(1 for r in recent_records if r.compliance_score and r.compliance_score >= 90),
                'good': sum(1 for r in recent_records if r.compliance_score and 80 <= r.compliance_score < 90),
                'fair': sum(1 for r in recent_records if r.compliance_score and 70 <= r.compliance_score < 80),
                'poor': sum(1 for r in recent_records if r.compliance_score and r.compliance_score < 70)
            }
            
            # Get recent audit snapshots
            recent_snapshots = self.db.query(AuditSnapshot).order_by(
                desc(AuditSnapshot.created_at)
            ).limit(10).all()
            
            # Get upcoming deadlines (mock data for now)
            upcoming_deadlines = [
                {
                    'framework': 'EPA',
                    'deadline': (datetime.now() + timedelta(days=30)).isoformat(),
                    'status': 'upcoming'
                },
                {
                    'framework': 'EU_ETS',
                    'deadline': (datetime.now() + timedelta(days=45)).isoformat(),
                    'status': 'upcoming'
                }
            ]
            
            return {
                'overview': {
                    'total_records': total_records,
                    'audit_ready_count': audit_ready_count,
                    'average_compliance_score': round(average_compliance_score, 2),
                    'compliance_rate': round((audit_ready_count / total_records * 100), 2) if total_records > 0 else 0
                },
                'score_distribution': score_distribution,
                'recent_snapshots': [
                    {
                        'submission_id': s.submission_id,
                        'submission_type': s.submission_type,
                        'submission_date': s.submission_date.isoformat(),
                        'total_records': s.total_records,
                        'average_compliance_score': float(s.average_compliance_score),
                        'submission_status': s.submission_status
                    }
                    for s in recent_snapshots
                ],
                'upcoming_deadlines': upcoming_deadlines,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting compliance dashboard data: {e}")
            return {
                'error': str(e),
                'last_updated': datetime.now().isoformat()
            }
    
    def generate_compliance_report(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive compliance report for an audit snapshot
        
        Args:
            snapshot_id: Audit snapshot submission ID
            
        Returns:
            Dictionary with comprehensive compliance report data
        """
        try:
            # Get audit snapshot
            snapshot = self.db.query(AuditSnapshot).filter(
                AuditSnapshot.submission_id == snapshot_id
            ).first()
            
            if not snapshot:
                raise ValueError(f"Audit snapshot {snapshot_id} not found")
            
            # Get all records in the snapshot period
            records = self.db.query(EmissionRecord).filter(
                and_(
                    EmissionRecord.created_at >= snapshot.reporting_period_start,
                    EmissionRecord.created_at <= snapshot.reporting_period_end
                )
            ).all()
            
            # Calculate compliance metrics
            total_records = len(records)
            audit_ready_count = sum(1 for r in records if r.audit_ready)
            non_compliant_count = sum(1 for r in records if r.compliance_score and r.compliance_score < 70)
            average_compliance_score = sum(float(r.compliance_score or 0) for r in records) / total_records if total_records > 0 else 0
            
            # Compliance score distribution
            compliance_score_ranges = {
                'excellent': sum(1 for r in records if r.compliance_score and r.compliance_score >= 90),
                'good': sum(1 for r in records if r.compliance_score and 80 <= r.compliance_score < 90),
                'fair': sum(1 for r in records if r.compliance_score and 70 <= r.compliance_score < 80),
                'poor': sum(1 for r in records if r.compliance_score and r.compliance_score < 70)
            }
            
            # Scope breakdown
            scope_breakdown = {}
            for record in records:
                scope = record.scope or 'unknown'
                scope_breakdown[scope] = scope_breakdown.get(scope, 0) + 1
            
            # Activity type breakdown
            activity_breakdown = {}
            for record in records:
                activity = record.activity_type or 'unknown'
                activity_breakdown[activity] = activity_breakdown.get(activity, 0) + 1
            
            # Collect all compliance flags
            all_compliance_flags = []
            for record in records:
                if record.compliance_flags:
                    # Handle both string and list formats
                    if isinstance(record.compliance_flags, str):
                        try:
                            import json
                            flags = json.loads(record.compliance_flags)
                            if isinstance(flags, list):
                                all_compliance_flags.extend(flags)
                            else:
                                all_compliance_flags.append(str(flags))
                        except (json.JSONDecodeError, TypeError):
                            # If it's not valid JSON, treat as a single flag
                            all_compliance_flags.append(str(record.compliance_flags))
                    elif isinstance(record.compliance_flags, list):
                        all_compliance_flags.extend(record.compliance_flags)
            
            # Determine regulatory status
            compliance_rate = (audit_ready_count / total_records * 100) if total_records > 0 else 0
            if compliance_rate >= 95:
                regulatory_status = 'excellent'
            elif compliance_rate >= 85:
                regulatory_status = 'good'
            elif compliance_rate >= 70:
                regulatory_status = 'fair'
            else:
                regulatory_status = 'poor'
            
            return {
                'snapshot_id': snapshot_id,
                'submission_type': snapshot.submission_type,
                'reporting_period': {
                    'start': snapshot.reporting_period_start.isoformat(),
                    'end': snapshot.reporting_period_end.isoformat()
                },
                'integrity': {
                    'merkle_root_hash': snapshot.merkle_root_hash,
                    'total_records': snapshot.total_records,
                    'total_emissions_kgco2e': float(snapshot.total_emissions_kgco2e)
                },
                'compliance_metrics': {
                    'average_compliance_score': round(average_compliance_score, 2),
                    'audit_ready_records': audit_ready_count,
                    'non_compliant_records': non_compliant_count,
                    'compliance_rate': round(compliance_rate, 2)
                },
                'regulatory_status': regulatory_status,
                'compliance_flags': list(set(all_compliance_flags)),  # Remove duplicates
                'records_summary': {
                    'total_records': total_records,
                    'compliance_score_ranges': compliance_score_ranges,
                    'scope_breakdown': scope_breakdown,
                    'activity_breakdown': activity_breakdown,
                    'audit_ready_count': audit_ready_count
                },
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            return {
                'error': str(e),
                'snapshot_id': snapshot_id
            }
