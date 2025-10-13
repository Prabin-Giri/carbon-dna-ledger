"""
Emissions calculation service for various data sources
Handles both structured data and freeform text extraction
"""
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
import logging
from sqlalchemy.orm import Session

from .. import models
from .factors import match_emission_factor, calculate_emissions
from .ai_classifier import AIClassifier
from .climate_trace import climate_trace_service
from .compliance_integrity_engine import ComplianceIntegrityEngine

logger = logging.getLogger(__name__)

class EmissionsCalculator:
    """Main emissions calculation service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_classifier = AIClassifier()
        self.compliance_engine = ComplianceIntegrityEngine(db)
    
    def calculate_emissions_if_missing(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate emissions if missing from the record
        Supports both spend-based and activity-based calculations
        """
        # Check if emissions already calculated
        if record.get('emissions_kgco2e') is not None:
            return record
        
        # Try different calculation methods
        calculation_methods = [
            self._calculate_from_spend_data,
            self._calculate_from_activity_data,
            self._calculate_from_llm_extraction
        ]
        
        for method in calculation_methods:
            try:
                result = method(record)
                if result:
                    record.update(result)
                    logger.info(f"Successfully calculated emissions using {method.__name__}")
                    
                    # Add Climate TRACE mapping after successful calculation
                    self._add_climate_trace_mapping(record)
                    
                    # Calculate compliance score after successful calculation
                    self._add_compliance_score(record)
                    
                    return record
            except Exception as e:
                logger.warning(f"Calculation method {method.__name__} failed: {str(e)}")
                continue
        
        # If all methods fail, raise exception
        raise ValueError(
            "Unable to calculate emissions: insufficient data. "
            "Required: either (amount + currency + ef_factor_per_currency) or "
            "(activity_amount + emission_factor_value) or freeform text for LLM extraction"
        )
    
    def _calculate_from_spend_data(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calculate emissions from spend-based data. If ef_factor is missing, derive it."""
        amount = record.get('amount')
        currency = record.get('currency')
        ef_factor = record.get('ef_factor_per_currency')
        
        if not amount or not currency:
            return None
        
        # Derive factor if not provided
        if ef_factor in (None, "", 0):
            try:
                ef_factor = self._get_emission_factor_for_spend(record)
            except Exception:
                return None
        
        try:
            emissions = float(amount) * float(ef_factor)
            method = 'spend_based' if record.get('ef_factor_per_currency') else 'spend_based_default_factor'
            return {
                'emissions_kgco2e': emissions,
                'calculation_method': method,
                'calculation_details': f"{amount} {currency} × {ef_factor} = {emissions:.2f} kg CO2e",
                'calculation_metadata': {
                    'type': 'spend_based',
                    'inputs': {
                        'amount': float(amount),
                        'currency': currency
                    },
                    'factor': {
                        'value': float(ef_factor),
                        'source': 'db_or_default',
                        'unit': 'kgCO2e per currency'
                    }
                }
            }
        except (ValueError, TypeError) as e:
            logger.error(f"Error in spend-based calculation: {e}")
            return None
    
    def _calculate_from_activity_data(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calculate emissions from activity-based data. If factor missing, derive it."""
        activity_amount = record.get('activity_amount')
        emission_factor_value = record.get('emission_factor_value')
        
        if not activity_amount:
            return None
        
        # Derive factor if missing
        if emission_factor_value in (None, "", 0):
            try:
                emission_factor_value = self._get_emission_factor_for_activity(record)
            except Exception:
                return None
        
        try:
            emissions = float(activity_amount) * float(emission_factor_value)
            method = 'activity_based' if record.get('emission_factor_value') else 'activity_based_default_factor'
            return {
                'emissions_kgco2e': emissions,
                'calculation_method': method,
                'calculation_details': f"{activity_amount} × {emission_factor_value} = {emissions:.2f} kg CO2e",
                'calculation_metadata': {
                    'type': 'activity_based',
                    'inputs': {
                        'activity_amount': float(activity_amount),
                        'activity_type': record.get('activity_type'),
                        'unit': record.get('activity_unit')
                    },
                    'factor': {
                        'value': float(emission_factor_value),
                        'source': 'db_or_default',
                        'unit': 'kgCO2e per unit'
                    }
                }
            }
        except (ValueError, TypeError) as e:
            logger.error(f"Error in activity-based calculation: {e}")
            return None
    
    def _calculate_from_llm_extraction(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calculate emissions by first extracting data using LLM, then calculating"""
        # Check if we have text to extract from
        text_sources = [
            record.get('description'),
            record.get('notes'),
            record.get('raw_row', {}).get('original_text') if isinstance(record.get('raw_row'), dict) else None
        ]
        
        text = next((t for t in text_sources if t and isinstance(t, str)), None)
        if not text:
            return None
        
        try:
            # Extract structured data using LLM
            extracted_data = self._extract_emission_data_with_llm(text, record.get('supplier_name'))
            
            if not extracted_data:
                return None
            
            # Try to calculate emissions from extracted data
            return self._calculate_from_extracted_data(record, extracted_data)
            
        except Exception as e:
            logger.error(f"Error in LLM extraction calculation: {e}")
            return None
    
    def _extract_emission_data_with_llm(self, text: str, supplier_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Extract emission-relevant data from freeform text using LLM"""
        try:
            # Use the existing AI classifier to extract structured data
            result = self.ai_classifier.classify_invoice_text(text, supplier_name)
            
            if not result.get('success'):
                return None
            
            data = result.get('data', {})
            
            # Extract key fields for emission calculation
            extracted = {
                'amount': self._safe_float(data.get('amount')),
                'currency': data.get('currency'),
                'activity_amount': self._safe_float(data.get('activity_amount')),
                'activity_type': data.get('activity_type'),
                'fuel_type': data.get('fuel_type'),
                'distance_km': self._safe_float(data.get('distance_km')),
                'mass_tonnes': self._safe_float(data.get('mass_tonnes')),
                'energy_kwh': self._safe_float(data.get('energy_kwh')),
                'scope': data.get('scope', 3),
                'category': data.get('category'),
                'subcategory': data.get('subcategory'),
                'description': data.get('description', text[:200])  # Truncate for storage
            }
            
            # Remove None values
            extracted = {k: v for k, v in extracted.items() if v is not None}
            
            return extracted if extracted else None
            
        except Exception as e:
            logger.error(f"Error in LLM extraction: {e}")
            return None
    
    def _calculate_from_extracted_data(self, record: Dict[str, Any], extracted_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calculate emissions from LLM-extracted data"""
        # First try spend-based calculation
        if all([extracted_data.get('amount'), extracted_data.get('currency')]):
            # Try to find emission factor for this currency/category
            ef_factor = self._get_emission_factor_for_spend(extracted_data)
            if ef_factor:
                emissions = float(extracted_data['amount']) * float(ef_factor)
                return {
                    'emissions_kgco2e': emissions,
                    'calculation_method': 'llm_extracted_spend',
                    'calculation_details': f"LLM extracted: {extracted_data['amount']} {extracted_data['currency']} × {ef_factor} = {emissions:.2f} kg CO2e",
                    'llm_extracted_data': extracted_data
                }
        
        # Then try activity-based calculation
        if extracted_data.get('activity_amount'):
            # Try to find emission factor for this activity
            ef_factor = self._get_emission_factor_for_activity(extracted_data)
            if ef_factor:
                emissions = float(extracted_data['activity_amount']) * float(ef_factor)
                return {
                    'emissions_kgco2e': emissions,
                    'calculation_method': 'llm_extracted_activity',
                    'calculation_details': f"LLM extracted: {extracted_data['activity_amount']} × {ef_factor} = {emissions:.2f} kg CO2e",
                    'llm_extracted_data': extracted_data
                }
        
        return None
    
    def _get_emission_factor_for_spend(self, data: Dict[str, Any]) -> Optional[float]:
        """Get emission factor for spend-based calculation"""
        currency = data.get('currency', 'USD')
        category = data.get('category', 'Other')
        scope = data.get('scope', 3)
        
        # Look for emission factor in database
        factor = self.db.query(models.EmissionFactor).filter(
            models.EmissionFactor.scope == scope,
            models.EmissionFactor.activity_category.ilike(f'%{category.lower()}%')
        ).first()
        
        if factor:
            return float(factor.value)
        
        # Fallback to default factors by currency
        default_factors = {
            'USD': 0.5,  # Default: $1 = 0.5 kg CO2e
            'EUR': 0.45,
            'GBP': 0.55,
            'CAD': 0.48,
            'AUD': 0.52
        }
        
        return default_factors.get(currency, 0.5)
    
    def _get_emission_factor_for_activity(self, data: Dict[str, Any]) -> Optional[float]:
        """Get emission factor for activity-based calculation"""
        activity_type = data.get('activity_type', 'other')
        scope = data.get('scope', 3)
        
        # Look for emission factor in database
        factor = self.db.query(models.EmissionFactor).filter(
            models.EmissionFactor.scope == scope,
            models.EmissionFactor.activity_category.ilike(f'%{activity_type.lower()}%')
        ).first()
        
        if factor:
            return float(factor.value)
        
        # Fallback to default factors by activity type
        default_factors = {
            'transportation': 0.2,  # kg CO2e per km
            'energy': 0.4,          # kg CO2e per kWh
            'waste': 0.1,           # kg CO2e per kg
            'materials': 0.3,       # kg CO2e per kg
            'other': 0.25
        }
        
        return default_factors.get(activity_type, 0.25)
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _add_climate_trace_mapping(self, record: Dict[str, Any]) -> None:
        """Add Climate TRACE taxonomy mapping to the record"""
        try:
            ct_mapping = climate_trace_service.map_activity_to_ct_taxonomy(record)
            record.update(ct_mapping)
            logger.debug(f"Added Climate TRACE mapping: {ct_mapping}")
        except Exception as e:
            logger.warning(f"Failed to add Climate TRACE mapping: {e}")
            # Don't fail the entire calculation if CT mapping fails
    
    def _add_compliance_score(self, record: Dict[str, Any]) -> None:
        """Add compliance score to the record"""
        try:
            compliance_score = self.compliance_engine.calculate_compliance_score(record)
            record.update({
                'compliance_score': compliance_score.overall_score,
                'factor_source_quality': compliance_score.factor_source_quality,
                'metadata_completeness': compliance_score.metadata_completeness,
                'data_entry_method_score': compliance_score.data_entry_method_score,
                'fingerprint_integrity': compliance_score.fingerprint_integrity,
                'llm_confidence': compliance_score.llm_confidence,
                'compliance_flags': compliance_score.compliance_flags,
                'audit_ready': compliance_score.audit_ready
            })
            logger.debug(f"Added compliance score: {compliance_score.overall_score}")
        except Exception as e:
            logger.warning(f"Failed to add compliance score: {e}")
            # Don't fail the entire calculation if compliance scoring fails
    
    def batch_calculate_emissions(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate emissions for multiple records"""
        results = []
        errors = []
        
        for i, record in enumerate(records):
            try:
                calculated_record = self.calculate_emissions_if_missing(record)
                results.append(calculated_record)
            except Exception as e:
                error_record = record.copy()
                error_record['calculation_error'] = str(e)
                error_record['emissions_kgco2e'] = None
                errors.append(error_record)
                logger.error(f"Error calculating emissions for record {i}: {e}")
        
        if errors:
            logger.warning(f"Failed to calculate emissions for {len(errors)} records")
        
        return results + errors
    
    def get_calculation_summary(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary of calculation methods used"""
        methods = {}
        total_emissions = 0
        calculated_count = 0
        
        for record in records:
            if record.get('emissions_kgco2e') is not None:
                calculated_count += 1
                total_emissions += float(record['emissions_kgco2e'])
                method = record.get('calculation_method', 'unknown')
                methods[method] = methods.get(method, 0) + 1
        
        return {
            'total_records': len(records),
            'calculated_records': calculated_count,
            'total_emissions_kgco2e': total_emissions,
            'calculation_methods': methods,
            'success_rate': calculated_count / len(records) if records else 0
        }


def calculate_emissions_if_missing(record: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    Standalone function to calculate emissions if missing
    This is the main entry point for the API
    """
    calculator = EmissionsCalculator(db)
    return calculator.calculate_emissions_if_missing(record)


def batch_calculate_emissions(records: List[Dict[str, Any]], db: Session) -> List[Dict[str, Any]]:
    """
    Standalone function to calculate emissions for multiple records
    """
    calculator = EmissionsCalculator(db)
    return calculator.batch_calculate_emissions(records)
