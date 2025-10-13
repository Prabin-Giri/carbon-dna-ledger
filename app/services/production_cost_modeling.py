"""
Production-grade cost modeling service
Comprehensive CAPEX/OPEX analysis with maintenance, regulatory, and market costs
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from datetime import datetime, date
import numpy as np

logger = logging.getLogger(__name__)

class ProductionCostModeling:
    """Production-grade cost modeling with comprehensive financial analysis"""
    
    def __init__(self, production_factors):
        self.factors = production_factors
        
    def calculate_comprehensive_costs(self, 
                                    original_record: Dict[str, Any], 
                                    changes: Dict[str, Any],
                                    analysis_period_years: int = 10) -> Dict[str, Any]:
        """
        Calculate comprehensive cost impact including CAPEX, OPEX, maintenance, and regulatory costs
        """
        try:
            # Get current costs
            current_costs = self._calculate_current_costs(original_record)
            
            # Calculate new costs with changes
            new_costs = self._calculate_new_costs(original_record, changes, analysis_period_years)
            
            # Calculate financial metrics
            financial_metrics = self._calculate_financial_metrics(current_costs, new_costs, analysis_period_years)
            
            # Calculate risk-adjusted costs
            risk_analysis = self._calculate_risk_analysis(current_costs, new_costs, changes)
            
            return {
                'current_costs': current_costs,
                'new_costs': new_costs,
                'financial_metrics': financial_metrics,
                'risk_analysis': risk_analysis,
                'analysis_period_years': analysis_period_years,
                'calculation_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive cost calculation: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_current_costs(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate current operational costs"""
        activity_type = record.get('activity_type', '').lower()
        activity_amount = record.get('activity_amount', 0)
        fuel_type = record.get('fuel_type', 'HFO')
        region = record.get('region', 'US')
        
        # Get current fuel price
        fuel_price_data = self.factors.get_market_prices(fuel_type, region)
        fuel_price = fuel_price_data.get('price', 0)
        
        # Calculate fuel costs
        if 'shipping' in activity_type or 'tanker' in activity_type:
            # Marine fuel costs (per tonne)
            fuel_cost = activity_amount * fuel_price
            fuel_cost_unit = 'USD/tonne'
        elif 'transportation' in activity_type:
            # Road transport costs (per liter)
            fuel_cost = activity_amount * fuel_price
            fuel_cost_unit = 'USD/liter'
        else:
            # Generic fuel costs
            fuel_cost = activity_amount * fuel_price
            fuel_cost_unit = 'USD/unit'
        
        # Calculate operational costs
        operational_costs = {
            'fuel_cost': fuel_cost,
            'fuel_cost_unit': fuel_cost_unit,
            'maintenance_cost': fuel_cost * 0.15,  # 15% of fuel cost
            'insurance_cost': fuel_cost * 0.05,    # 5% of fuel cost
            'crew_cost': fuel_cost * 0.20,         # 20% of fuel cost
            'port_fees': fuel_cost * 0.10,         # 10% of fuel cost
            'total_operational': fuel_cost * 1.50  # Total OPEX
        }
        
        # Calculate regulatory costs
        regulatory_costs = self._calculate_regulatory_costs(record, fuel_type, region)
        
        # Calculate total current costs
        total_current = operational_costs['total_operational'] + regulatory_costs['total_regulatory']
        
        return {
            'operational_costs': operational_costs,
            'regulatory_costs': regulatory_costs,
            'total_annual_cost': total_current,
            'cost_breakdown': {
                'fuel_pct': (fuel_cost / total_current) * 100,
                'maintenance_pct': (operational_costs['maintenance_cost'] / total_current) * 100,
                'regulatory_pct': (regulatory_costs['total_regulatory'] / total_current) * 100,
                'other_pct': ((total_current - fuel_cost - operational_costs['maintenance_cost'] - regulatory_costs['total_regulatory']) / total_current) * 100
            }
        }
    
    def _calculate_new_costs(self, record: Dict[str, Any], changes: Dict[str, Any], analysis_period: int) -> Dict[str, Any]:
        """Calculate new costs with proposed changes"""
        # Calculate CAPEX for changes
        capex_analysis = self._calculate_capex_analysis(changes, analysis_period)
        
        # Calculate new operational costs
        new_operational = self._calculate_new_operational_costs(record, changes)
        
        # Calculate new regulatory costs
        new_regulatory = self._calculate_new_regulatory_costs(record, changes)
        
        # Calculate total new costs
        total_new_annual = new_operational['total_operational'] + new_regulatory['total_regulatory']
        total_new_with_capex = total_new_annual + (capex_analysis['annual_capex'] if capex_analysis else 0)
        
        return {
            'capex_analysis': capex_analysis,
            'operational_costs': new_operational,
            'regulatory_costs': new_regulatory,
            'total_annual_cost': total_new_annual,
            'total_with_capex': total_new_with_capex,
            'cost_breakdown': {
                'capex_pct': ((capex_analysis['annual_capex'] if capex_analysis else 0) / total_new_with_capex) * 100,
                'fuel_pct': (new_operational['fuel_cost'] / total_new_with_capex) * 100,
                'maintenance_pct': (new_operational['maintenance_cost'] / total_new_with_capex) * 100,
                'regulatory_pct': (new_regulatory['total_regulatory'] / total_new_with_capex) * 100
            }
        }
    
    def _calculate_capex_analysis(self, changes: Dict[str, Any], analysis_period: int) -> Optional[Dict[str, Any]]:
        """Calculate CAPEX requirements for changes"""
        capex_items = []
        total_capex = 0
        
        # Fuel switch CAPEX
        if 'fuel_type' in changes:
            fuel_switch_capex = self._calculate_fuel_switch_capex(changes)
            if fuel_switch_capex:
                capex_items.append(fuel_switch_capex)
                total_capex += fuel_switch_capex['total_cost']
        
        # Renewable energy CAPEX
        if 'renewable_percent' in changes:
            renewable_capex = self._calculate_renewable_capex(changes)
            if renewable_capex:
                capex_items.append(renewable_capex)
                total_capex += renewable_capex['total_cost']
        
        # Efficiency upgrade CAPEX
        if 'efficiency_improvement_percent' in changes:
            efficiency_capex = self._calculate_efficiency_capex(changes)
            if efficiency_capex:
                capex_items.append(efficiency_capex)
                total_capex += efficiency_capex['total_cost']
        
        if not capex_items:
            return None
        
        # Calculate annualized CAPEX
        annual_capex = total_capex / analysis_period
        
        return {
            'capex_items': capex_items,
            'total_capex': total_capex,
            'annual_capex': annual_capex,
            'analysis_period_years': analysis_period,
            'depreciation_method': 'straight_line'
        }
    
    def _calculate_fuel_switch_capex(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate CAPEX for fuel switching"""
        new_fuel = changes.get('fuel_type')
        fuel_switch_costs = {
            'LNG': {'engine_modification': 5000000, 'storage_tanks': 2000000, 'safety_systems': 1000000},
            'Methanol': {'engine_modification': 3000000, 'storage_tanks': 1500000, 'safety_systems': 800000},
            'Hydrogen': {'engine_modification': 8000000, 'storage_tanks': 5000000, 'safety_systems': 2000000},
            'Ammonia': {'engine_modification': 6000000, 'storage_tanks': 3000000, 'safety_systems': 1500000}
        }
        
        costs = fuel_switch_costs.get(new_fuel)
        if not costs:
            return None
        
        total_cost = sum(costs.values())
        
        return {
            'change_type': 'fuel_switch',
            'new_fuel': new_fuel,
            'cost_breakdown': costs,
            'total_cost': total_cost,
            'payback_period_years': 8,  # Industry average
            'maintenance_increase_pct': 20  # Increased maintenance for new fuel
        }
    
    def _calculate_renewable_capex(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate CAPEX for renewable energy investments"""
        renewable_percent = changes.get('renewable_percent', 0)
        
        # Solar installation costs (USD per kW)
        solar_cost_per_kw = 2500
        wind_cost_per_kw = 1500
        
        # Assume 1 MW system for marine vessel
        system_size_kw = 1000
        renewable_capacity = system_size_kw * (renewable_percent / 100)
        
        solar_capex = renewable_capacity * solar_cost_per_kw
        wind_capex = renewable_capacity * wind_cost_per_kw
        
        total_cost = (solar_capex + wind_capex) / 2  # Average of solar and wind
        
        return {
            'change_type': 'renewable_energy',
            'renewable_percent': renewable_percent,
            'system_size_kw': renewable_capacity,
            'solar_capex': solar_capex,
            'wind_capex': wind_capex,
            'total_cost': total_cost,
            'payback_period_years': 12,
            'maintenance_cost_pct': 2  # 2% of CAPEX annually
        }
    
    def _calculate_efficiency_capex(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate CAPEX for efficiency improvements"""
        efficiency_percent = changes.get('efficiency_improvement_percent', 0)
        
        # Efficiency improvement costs scale with improvement percentage
        base_cost = 1000000  # Base cost for 10% improvement
        cost_multiplier = (efficiency_percent / 10) ** 1.5  # Non-linear scaling
        
        total_cost = base_cost * cost_multiplier
        
        return {
            'change_type': 'efficiency_upgrade',
            'efficiency_percent': efficiency_percent,
            'total_cost': total_cost,
            'payback_period_years': 5,
            'maintenance_cost_pct': 1  # 1% of CAPEX annually
        }
    
    def _calculate_new_operational_costs(self, record: Dict[str, Any], changes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate new operational costs with changes"""
        # Start with current operational costs
        current_costs = self._calculate_current_costs(record)
        base_operational = current_costs['operational_costs']
        
        # Apply fuel type changes
        if 'fuel_type' in changes:
            new_fuel = changes['fuel_type']
            region = record.get('region', 'US')
            new_fuel_price = self.factors.get_market_prices(new_fuel, region)
            fuel_cost = record.get('activity_amount', 0) * new_fuel_price.get('price', 0)
        else:
            fuel_cost = base_operational['fuel_cost']
        
        # Apply efficiency improvements
        if 'efficiency_improvement_percent' in changes:
            efficiency_gain = changes['efficiency_improvement_percent']
            fuel_cost *= (1 - efficiency_gain / 100)
        
        # Apply renewable energy
        if 'renewable_percent' in changes:
            renewable_percent = changes['renewable_percent']
            fuel_cost *= (1 - renewable_percent / 100)
        
        # Calculate other operational costs
        maintenance_cost = fuel_cost * 0.15
        insurance_cost = fuel_cost * 0.05
        crew_cost = fuel_cost * 0.20
        port_fees = fuel_cost * 0.10
        
        # Add maintenance increase for new technologies
        maintenance_increase = 0
        if 'fuel_type' in changes:
            fuel_switch_capex = self._calculate_fuel_switch_capex(changes)
            if fuel_switch_capex:
                maintenance_increase = fuel_switch_capex.get('maintenance_increase_pct', 0)
        
        if 'renewable_percent' in changes:
            renewable_capex = self._calculate_renewable_capex(changes)
            if renewable_capex:
                maintenance_increase += renewable_capex.get('maintenance_cost_pct', 0)
        
        maintenance_cost *= (1 + maintenance_increase / 100)
        
        total_operational = fuel_cost + maintenance_cost + insurance_cost + crew_cost + port_fees
        
        return {
            'fuel_cost': fuel_cost,
            'maintenance_cost': maintenance_cost,
            'insurance_cost': insurance_cost,
            'crew_cost': crew_cost,
            'port_fees': port_fees,
            'total_operational': total_operational,
            'maintenance_increase_pct': maintenance_increase
        }
    
    def _calculate_regulatory_costs(self, record: Dict[str, Any], fuel_type: str, region: str) -> Dict[str, Any]:
        """Calculate regulatory compliance costs"""
        activity_type = record.get('activity_type', '').lower()
        
        # Base regulatory costs
        base_regulatory = {
            'emissions_reporting': 5000,  # Annual reporting costs
            'compliance_monitoring': 10000,  # Monitoring equipment and personnel
            'permits_licenses': 2000,  # Annual permit costs
            'audit_costs': 15000,  # Third-party audit costs
            'total_regulatory': 32000
        }
        
        # Additional costs for specific fuel types
        fuel_specific_costs = {
            'LNG': {'additional_permits': 5000, 'safety_certifications': 10000},
            'Methanol': {'additional_permits': 3000, 'safety_certifications': 8000},
            'Hydrogen': {'additional_permits': 10000, 'safety_certifications': 15000},
            'Ammonia': {'additional_permits': 8000, 'safety_certifications': 12000}
        }
        
        additional_costs = fuel_specific_costs.get(fuel_type, {'additional_permits': 0, 'safety_certifications': 0})
        
        # Regional regulatory costs
        regional_costs = {
            'US': {'carbon_tax': 0, 'additional_fees': 0},  # No federal carbon tax
            'EU': {'carbon_tax': 5000, 'additional_fees': 2000},  # EU ETS
            'Asia': {'carbon_tax': 2000, 'additional_fees': 1000}
        }
        
        regional_additional = regional_costs.get(region, {'carbon_tax': 0, 'additional_fees': 0})
        
        total_additional = (additional_costs['additional_permits'] + 
                          additional_costs['safety_certifications'] + 
                          regional_additional['carbon_tax'] + 
                          regional_additional['additional_fees'])
        
        return {
            **base_regulatory,
            'fuel_specific_costs': additional_costs,
            'regional_costs': regional_additional,
            'total_additional': total_additional,
            'total_regulatory': base_regulatory['total_regulatory'] + total_additional
        }
    
    def _calculate_new_regulatory_costs(self, record: Dict[str, Any], changes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate new regulatory costs with changes"""
        # Start with current regulatory costs
        current_regulatory = self._calculate_regulatory_costs(record, record.get('fuel_type', 'HFO'), record.get('region', 'US'))
        
        # Apply changes
        new_fuel = changes.get('fuel_type', record.get('fuel_type', 'HFO'))
        new_region = changes.get('region', record.get('region', 'US'))
        
        return self._calculate_regulatory_costs(record, new_fuel, new_region)
    
    def _calculate_financial_metrics(self, current_costs: Dict[str, Any], new_costs: Dict[str, Any], analysis_period: int) -> Dict[str, Any]:
        """Calculate comprehensive financial metrics"""
        current_annual = current_costs['total_annual_cost']
        new_annual = new_costs['total_annual_cost']
        
        # Annual savings
        annual_savings = current_annual - new_annual
        
        # CAPEX analysis
        capex_analysis = new_costs.get('capex_analysis')
        total_capex = capex_analysis['total_capex'] if capex_analysis else 0
        
        # Payback period
        if annual_savings > 0 and total_capex > 0:
            payback_period = total_capex / annual_savings
        else:
            payback_period = float('inf') if total_capex > 0 else 0
        
        # Net Present Value (NPV) - 10% discount rate
        discount_rate = 0.10
        npv = 0
        for year in range(1, analysis_period + 1):
            npv += annual_savings / ((1 + discount_rate) ** year)
        npv -= total_capex
        
        # Internal Rate of Return (IRR) - simplified calculation
        if total_capex > 0 and annual_savings > 0:
            irr = (annual_savings / total_capex) ** (1/analysis_period) - 1
        else:
            irr = 0
        
        # Return on Investment (ROI)
        roi = (annual_savings * analysis_period - total_capex) / total_capex if total_capex > 0 else 0
        
        return {
            'annual_savings': annual_savings,
            'total_capex': total_capex,
            'payback_period_years': payback_period,
            'npv_usd': npv,
            'irr_percent': irr * 100,
            'roi_percent': roi * 100,
            'analysis_period_years': analysis_period,
            'discount_rate_percent': discount_rate * 100
        }
    
    def _calculate_risk_analysis(self, current_costs: Dict[str, Any], new_costs: Dict[str, Any], changes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk-adjusted cost analysis"""
        # Price volatility analysis
        fuel_volatility = self._analyze_fuel_price_volatility(changes)
        
        # Technology risk analysis
        technology_risk = self._analyze_technology_risk(changes)
        
        # Regulatory risk analysis
        regulatory_risk = self._analyze_regulatory_risk(changes)
        
        # Combined risk score (0-100, higher = riskier)
        combined_risk_score = (fuel_volatility['risk_score'] + 
                              technology_risk['risk_score'] + 
                              regulatory_risk['risk_score']) / 3
        
        return {
            'fuel_volatility': fuel_volatility,
            'technology_risk': technology_risk,
            'regulatory_risk': regulatory_risk,
            'combined_risk_score': combined_risk_score,
            'risk_level': self._get_risk_level(combined_risk_score)
        }
    
    def _analyze_fuel_price_volatility(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze fuel price volatility risk"""
        if 'fuel_type' not in changes:
            return {'risk_score': 0, 'volatility_pct': 0, 'risk_factors': []}
        
        new_fuel = changes['fuel_type']
        fuel_volatilities = {
            'HFO': 0.15,
            'VLSFO': 0.12,
            'MGO': 0.10,
            'LNG': 0.20,
            'Methanol': 0.25,
            'Hydrogen': 0.30,
            'Ammonia': 0.28
        }
        
        volatility = fuel_volatilities.get(new_fuel, 0.15)
        risk_score = min(volatility * 100, 100)
        
        risk_factors = []
        if volatility > 0.20:
            risk_factors.append('High price volatility')
        if new_fuel in ['Hydrogen', 'Ammonia']:
            risk_factors.append('Emerging technology pricing')
        
        return {
            'risk_score': risk_score,
            'volatility_pct': volatility * 100,
            'risk_factors': risk_factors
        }
    
    def _analyze_technology_risk(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze technology maturity and implementation risk"""
        risk_score = 0
        risk_factors = []
        
        if 'fuel_type' in changes:
            new_fuel = changes['fuel_type']
            if new_fuel in ['Hydrogen', 'Ammonia']:
                risk_score += 40
                risk_factors.append('Emerging technology')
            elif new_fuel in ['LNG', 'Methanol']:
                risk_score += 20
                risk_factors.append('Developing technology')
        
        if 'renewable_percent' in changes:
            renewable_percent = changes['renewable_percent']
            if renewable_percent > 50:
                risk_score += 30
                risk_factors.append('High renewable integration')
        
        if 'efficiency_improvement_percent' in changes:
            efficiency_percent = changes['efficiency_improvement_percent']
            if efficiency_percent > 20:
                risk_score += 25
                risk_factors.append('High efficiency improvement')
        
        return {
            'risk_score': min(risk_score, 100),
            'risk_factors': risk_factors
        }
    
    def _analyze_regulatory_risk(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze regulatory compliance risk"""
        risk_score = 0
        risk_factors = []
        
        if 'fuel_type' in changes:
            new_fuel = changes['fuel_type']
            if new_fuel in ['Hydrogen', 'Ammonia']:
                risk_score += 35
                risk_factors.append('New fuel regulations')
            elif new_fuel in ['LNG', 'Methanol']:
                risk_score += 15
                risk_factors.append('Evolving fuel standards')
        
        return {
            'risk_score': min(risk_score, 100),
            'risk_factors': risk_factors
        }
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level"""
        if risk_score < 25:
            return 'Low'
        elif risk_score < 50:
            return 'Medium'
        elif risk_score < 75:
            return 'High'
        else:
            return 'Very High'
