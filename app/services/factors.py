"""
Emission factor matching and calculation services
"""
from typing import Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .. import models

def match_emission_factor(db: Session, record: Dict[str, Any]) -> Optional[models.EmissionFactor]:
    """
    Match emission factor based on activity, region, and other attributes
    Uses rule-based matching logic
    """
    activity = record.get('activity', '').lower()
    region = record.get('region', '')
    fuel_type = record.get('fuel_type', '').lower() if 'fuel_type' in record else None
    scope = record.get('scope', 3)
    
    # Determine activity category
    if 'tanker' in activity or 'shipping' in activity or 'vessel' in activity:
        activity_category = 'shipping'
    elif 'electricity' in activity or 'power' in activity:
        activity_category = 'electricity'
    elif 'refinery' in activity:
        activity_category = 'refinery'
    else:
        activity_category = 'general'
    
    # Build query
    query = db.query(models.EmissionFactor).filter(
        models.EmissionFactor.activity_category == activity_category,
        models.EmissionFactor.scope == scope
    )
    
    # Add region filter if available
    if region:
        query = query.filter(
            models.EmissionFactor.region.ilike(f'%{region}%')
        )
    
    # For shipping, prioritize fuel type matching
    if activity_category == 'shipping' and fuel_type:
        fuel_query = query.filter(
            models.EmissionFactor.description.ilike(f'%{fuel_type}%')
        )
        factor = fuel_query.first()
        if factor:
            return factor
    
    # Fall back to general match
    factor = query.first()
    
    # If no region-specific factor, try global
    if not factor and region:
        factor = db.query(models.EmissionFactor).filter(
            models.EmissionFactor.activity_category == activity_category,
            models.EmissionFactor.scope == scope,
            models.EmissionFactor.region.is_(None)
        ).first()
    
    return factor

def calculate_emissions(record: Dict[str, Any], factor: models.EmissionFactor) -> Dict[str, Any]:
    """
    Calculate emissions based on input parameters and emission factor
    Returns calculation method, result, and quality assessment
    """
    inputs = record.get('inputs', {})
    
    # Initialize calculation components
    result_kgco2e = 0.0
    method_parts = []
    uncertainty_pct = float(factor.uncertainty_pct or 0)
    quality_flags = []
    
    # Determine calculation method based on activity and available inputs
    if factor.activity_category == 'shipping':
        distance_km = inputs.get('distance_km')
        tonnage = inputs.get('tonnage')
        
        if distance_km and tonnage:
            result_kgco2e = float(distance_km) * float(tonnage) * float(factor.value)
            method_parts = ['distance_km', 'tonnage', 'factor']
        elif distance_km:
            result_kgco2e = float(distance_km) * float(factor.value)
            method_parts = ['distance_km', 'factor']
            uncertainty_pct += 15  # Higher uncertainty without tonnage
            quality_flags.append('missing_tonnage')
        else:
            quality_flags.append('incomplete')
            uncertainty_pct += 25
            result_kgco2e = 1000  # Default estimate
            method_parts = ['default_estimate']
            
    elif factor.activity_category == 'electricity':
        kwh = inputs.get('kwh')
        grid_mix_renewables = inputs.get('grid_mix_renewables', 0)
        
        if kwh:
            # Adjust factor based on renewable mix if available
            adjusted_factor = float(factor.value)
            if grid_mix_renewables:
                renewable_factor = 1 - (float(grid_mix_renewables) / 100)
                adjusted_factor *= renewable_factor
                method_parts = ['kwh', 'adjusted_factor', '(renewable_mix)']
            else:
                method_parts = ['kwh', 'factor']
            
            result_kgco2e = float(kwh) * adjusted_factor
        else:
            quality_flags.append('incomplete')
            uncertainty_pct += 25
            result_kgco2e = 100  # Default estimate
            method_parts = ['default_estimate']
    
    else:
        # Generic calculation
        # Try to use any numeric input
        numeric_inputs = {k: v for k, v in inputs.items() if isinstance(v, (int, float, Decimal))}
        if numeric_inputs:
            # Use first numeric input
            input_key, input_value = next(iter(numeric_inputs.items()))
            result_kgco2e = float(input_value) * float(factor.value)
            method_parts = [input_key, 'factor']
        else:
            quality_flags.append('incomplete')
            uncertainty_pct += 25
            result_kgco2e = 50  # Default estimate
            method_parts = ['default_estimate']
    
    # Build method string
    method = ' * '.join(method_parts)
    
    return {
        'result_kgco2e': result_kgco2e,
        'method': method,
        'uncertainty_pct': uncertainty_pct,
        'quality_flags': quality_flags
    }

def get_factor_catalog(db: Session) -> Dict[str, Any]:
    """
    Get complete emission factor catalog for reference
    """
    factors = db.query(models.EmissionFactor).all()
    
    catalog = {}
    for factor in factors:
        key = f"{factor.activity_category}_{factor.scope}_{factor.region or 'global'}"
        catalog[key] = {
            'id': str(factor.id),
            'source': factor.source,
            'description': factor.description,
            'value': float(factor.value),
            'unit': factor.unit,
            'version': factor.version,
            'uncertainty_pct': float(factor.uncertainty_pct or 0)
        }
    
    return catalog

def suggest_better_factor(db: Session, current_factor_id: str, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Suggest potentially better emission factor based on improved data
    """
    current_factor = db.query(models.EmissionFactor).filter(
        models.EmissionFactor.id == current_factor_id
    ).first()
    
    if not current_factor:
        return None
    
    # Look for more recent version
    better_factor = db.query(models.EmissionFactor).filter(
        models.EmissionFactor.activity_category == current_factor.activity_category,
        models.EmissionFactor.scope == current_factor.scope,
        models.EmissionFactor.region == current_factor.region,
        models.EmissionFactor.uncertainty_pct < current_factor.uncertainty_pct
    ).order_by(models.EmissionFactor.uncertainty_pct).first()
    
    if better_factor and better_factor.id != current_factor.id:
        return {
            'suggested_id': str(better_factor.id),
            'improvement': 'lower_uncertainty',
            'current_uncertainty': float(current_factor.uncertainty_pct or 0),
            'suggested_uncertainty': float(better_factor.uncertainty_pct or 0),
            'source': better_factor.source,
            'version': better_factor.version
        }
    
    return None
