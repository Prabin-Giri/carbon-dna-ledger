"""
What-if scenario analysis services
"""
from typing import Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session

from .. import models
from . import factors

def run_scenario_analysis(
    db: Session, 
    event: models.CarbonEvent, 
    current_factor: models.EmissionFactor,
    changes: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run what-if scenario analysis by modifying event parameters
    Returns before/after comparison with percentage change
    """
    
    # Get original values for comparison
    original_inputs = dict(event.inputs)
    original_result = float(event.result_kgco2e)
    original_factor_ref = f"{current_factor.source} v{current_factor.version}"
    
    # Create modified record for recalculation
    modified_record = {
        'activity': event.activity,
        'scope': event.scope,
        'region': original_inputs.get('region', ''),
        'fuel_type': original_inputs.get('fuel_type', ''),
        'inputs': original_inputs.copy()
    }
    
    # Track what changed
    changed_tokens = []
    
    # Apply changes to inputs
    for key, value in changes.items():
        if key == 'factor_override_id':
            continue  # Handle separately
        
        if value is not None:
            modified_record['inputs'][key] = value
            changed_tokens.append(key)
            
            # Update top-level fields if they affect factor matching
            if key == 'fuel_type':
                modified_record['fuel_type'] = value
    
    # Determine which emission factor to use
    new_factor = current_factor
    if 'factor_override_id' in changes and changes['factor_override_id']:
        # Use explicitly specified factor
        new_factor = db.query(models.EmissionFactor).filter(
            models.EmissionFactor.id == changes['factor_override_id']
        ).first()
        if new_factor:
            changed_tokens.append('factor_override')
    else:
        # Try to find better matching factor based on changes
        if 'fuel_type' in changes or any(key in changes for key in ['region']):
            matched_factor = factors.match_emission_factor(db, modified_record)
            if matched_factor and matched_factor.id != current_factor.id:
                new_factor = matched_factor
                changed_tokens.append('auto_factor_match')
    
    # Recalculate emissions with new parameters
    new_calculation = factors.calculate_emissions(modified_record, new_factor)
    new_result = new_calculation['result_kgco2e']
    new_factor_ref = f"{new_factor.source} v{new_factor.version}"
    
    # Calculate percentage change
    if original_result > 0:
        pct_change = ((new_result - original_result) / original_result) * 100
    else:
        pct_change = 0 if new_result == 0 else 100
    
    return {
        'before': {
            'result_kgco2e': original_result,
            'factor_ref': original_factor_ref,
            'factor_value': float(current_factor.value),
            'method': event.method,
            'inputs': original_inputs
        },
        'after': {
            'result_kgco2e': new_result,
            'factor_ref': new_factor_ref,
            'factor_value': float(new_factor.value),
            'method': new_calculation['method'],
            'inputs': modified_record['inputs']
        },
        'pct_change': round(pct_change, 2),
        'changed_tokens': changed_tokens,
        'calculation_details': {
            'uncertainty_change': new_calculation['uncertainty_pct'] - float(event.uncertainty_pct or 0),
            'quality_flags': new_calculation.get('quality_flags', [])
        }
    }

def compare_fuel_scenarios(
    db: Session,
    event: models.CarbonEvent,
    fuel_options: list
) -> Dict[str, Any]:
    """
    Compare emissions across different fuel type scenarios
    Useful for shipping route optimization
    """
    results = {}
    
    for fuel_type in fuel_options:
        scenario_result = run_scenario_analysis(
            db, event, 
            db.query(models.EmissionFactor).filter(models.EmissionFactor.id == event.factor_id).first(),
            {'fuel_type': fuel_type}
        )
        
        results[fuel_type] = {
            'result_kgco2e': scenario_result['after']['result_kgco2e'],
            'pct_vs_original': scenario_result['pct_change'],
            'factor_ref': scenario_result['after']['factor_ref']
        }
    
    # Find best and worst options
    best_fuel = min(results.keys(), key=lambda x: results[x]['result_kgco2e'])
    worst_fuel = max(results.keys(), key=lambda x: results[x]['result_kgco2e'])
    
    return {
        'scenarios': results,
        'recommendations': {
            'best_option': {
                'fuel_type': best_fuel,
                'savings_kgco2e': results[worst_fuel]['result_kgco2e'] - results[best_fuel]['result_kgco2e'],
                'savings_pct': ((results[worst_fuel]['result_kgco2e'] - results[best_fuel]['result_kgco2e']) / results[worst_fuel]['result_kgco2e']) * 100
            }
        }
    }

def sensitivity_analysis(
    db: Session,
    event: models.CarbonEvent,
    parameter: str,
    variation_range: float = 0.2
) -> Dict[str, Any]:
    """
    Perform sensitivity analysis by varying a parameter within a range
    Returns impact assessment
    """
    current_factor = db.query(models.EmissionFactor).filter(
        models.EmissionFactor.id == event.factor_id
    ).first()
    
    original_value = event.inputs.get(parameter)
    if not original_value or not isinstance(original_value, (int, float, Decimal)):
        return {'error': f'Parameter {parameter} not found or not numeric'}
    
    original_value = float(original_value)
    variations = [-variation_range, -variation_range/2, 0, variation_range/2, variation_range]
    results = []
    
    for variation in variations:
        new_value = original_value * (1 + variation)
        scenario = run_scenario_analysis(
            db, event, current_factor,
            {parameter: new_value}
        )
        
        results.append({
            'variation_pct': variation * 100,
            'parameter_value': new_value,
            'result_kgco2e': scenario['after']['result_kgco2e'],
            'change_pct': scenario['pct_change']
        })
    
    # Calculate sensitivity coefficient
    # How much % change in emissions per % change in parameter
    if len(results) >= 2:
        param_change = (results[-1]['parameter_value'] - results[0]['parameter_value']) / original_value * 100
        emission_change = results[-1]['change_pct'] - results[0]['change_pct']
        sensitivity = emission_change / param_change if param_change != 0 else 0
    else:
        sensitivity = 0
    
    return {
        'parameter': parameter,
        'sensitivity_coefficient': round(sensitivity, 3),
        'interpretation': 'high' if abs(sensitivity) > 0.8 else 'medium' if abs(sensitivity) > 0.3 else 'low',
        'variations': results
    }
