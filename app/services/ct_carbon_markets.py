"""
Climate TRACE Carbon Markets Integration
Integrates with carbon markets and verifies projects against Climate TRACE data
"""
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from sqlalchemy.orm import Session

from ..models import EmissionRecord, ClimateTraceCrosscheck

logger = logging.getLogger(__name__)

@dataclass
class MarketPrice:
    """Carbon credit market price data"""
    standard: str
    project_type: str
    price_per_ton: float
    currency: str
    volume_available: int
    last_updated: datetime

@dataclass
class CarbonProject:
    """Carbon project with Climate TRACE verification"""
    project_id: str
    project_name: str
    project_type: str
    location: str
    standard: str
    total_credits: int
    issued_credits: int
    retired_credits: int
    available_credits: int
    verification_status: str
    climate_trace_emissions: Optional[float]
    our_emissions: Optional[Dict[str, Any]]
    verification_delta: Optional[float]
    eligibility_score: float

class ClimateTraceCarbonMarkets:
    """Service for carbon markets integration with Climate TRACE verification"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.carbon_standards = {
            'VCS': {
                'name': 'Verified Carbon Standard',
                'price_range': [5.0, 20.0],
                'api_endpoint': 'https://api.v-c-s.org'  # Placeholder
            },
            'GS': {
                'name': 'Gold Standard',
                'price_range': [8.0, 25.0],
                'api_endpoint': 'https://api.goldstandard.org'  # Placeholder
            },
            'CAR': {
                'name': 'Climate Action Reserve',
                'price_range': [6.0, 18.0],
                'api_endpoint': 'https://api.climateactionreserve.org'  # Placeholder
            }
        }
        
        # Map project types to Climate TRACE sectors
        self.project_type_mapping = {
            'forest_conservation': 'forest-land-clearing',
            'renewable_energy': 'electricity-generation',
            'cookstove': 'other',
            'waste_management': 'waste',
            'transportation': 'transportation'
        }
    
    def verify_carbon_project(self, project_id: str, standard: str) -> CarbonProject:
        """
        Verify a carbon project against Climate TRACE data
        
        Args:
            project_id: Carbon project identifier
            standard: Carbon standard (VCS, GS, CAR)
            
        Returns:
            Verified carbon project with Climate TRACE data
        """
        try:
            # Get project data from carbon registry
            project_data = self._fetch_project_data(project_id, standard)
            if not project_data:
                raise ValueError(f"Project {project_id} not found in {standard} registry")
            
            # Get Climate TRACE data for verification
            ct_data = self._get_climate_trace_data_for_project(project_data)
            
            # Calculate verification delta
            verification_delta = None
            if ct_data and project_data.get('emissions_data'):
                our_emissions = project_data['emissions_data']  # tons CO2e
                ct_emissions = ct_data['emissions_kgco2e'] / 1000  # Convert kg to tons
                verification_delta = ((our_emissions - ct_emissions) / ct_emissions) * 100
            
            # Calculate eligibility score
            eligibility_score = self._calculate_eligibility_score(project_data, ct_data, verification_delta)
            
            return CarbonProject(
                project_id=project_id,
                project_name=project_data.get('name', 'Unknown'),
                project_type=project_data.get('type', 'Unknown'),
                location=project_data.get('location', 'Unknown'),
                standard=standard,
                total_credits=project_data.get('total_credits', 0),
                issued_credits=project_data.get('issued_credits', 0),
                retired_credits=project_data.get('retired_credits', 0),
                available_credits=project_data.get('available_credits', 0),
                verification_status=project_data.get('verification_status', 'pending'),
                climate_trace_emissions=ct_data.get('emissions_kgco2e') if ct_data else None,
                our_emissions=project_data.get('emissions_data'),
                verification_delta=verification_delta,
                eligibility_score=eligibility_score
            )
            
        except Exception as e:
            logger.error(f"Error verifying carbon project: {e}")
            raise
    
    def _fetch_project_data(self, project_id: str, standard: str) -> Optional[Dict[str, Any]]:
        """Fetch project data from carbon registry (placeholder implementation)"""
        # This would integrate with actual carbon registry APIs
        # For now, return mock data
        
        mock_projects = {
            'VCS_001': {
                'name': 'Amazon Rainforest Conservation Project',
                'type': 'forest_conservation',
                'location': 'Brazil',
                'total_credits': 100000,
                'issued_credits': 75000,
                'retired_credits': 25000,
                'available_credits': 50000,
                'verification_status': 'verified',
                'emissions_data': 50000  # tons CO2e avoided
            },
            'GS_002': {
                'name': 'Solar Power Development in India',
                'type': 'renewable_energy',
                'location': 'India',
                'total_credits': 50000,
                'issued_credits': 30000,
                'retired_credits': 10000,
                'available_credits': 20000,
                'verification_status': 'verified',
                'emissions_data': 25000  # tons CO2e avoided
            }
        }
        
        return mock_projects.get(f"{standard}_{project_id}")
    
    def _get_climate_trace_data_for_project(self, project_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get Climate TRACE data for project location and type"""
        try:
            # Map project type to Climate TRACE sector
            project_type = project_data.get('type', '')
            location = project_data.get('location', '')
            
            # Simple mapping for demonstration
            if 'forest' in project_type.lower():
                sector = 'forest-land-clearing'
            elif 'renewable' in project_type.lower() or 'solar' in project_type.lower():
                sector = 'electricity-generation'
            elif 'wind' in project_type.lower():
                sector = 'electricity-generation'
            else:
                sector = 'other'
            
            # Map location to country code
            country_mapping = {
                'brazil': 'BRA',
                'india': 'IND',
                'china': 'CHN',
                'united states': 'USA',
                'usa': 'USA'
            }
            
            country_code = country_mapping.get(location.lower(), 'UNK')
            
            # This would call the actual Climate TRACE API
            # For now, return mock data
            return {
                'sector': sector,
                'country_code': country_code,
                'emissions_kgco2e': project_data.get('emissions_data', 0) * 1000,  # Convert tons to kg
                'confidence': 'high',
                'data_source': 'Climate TRACE API'
            }
            
        except Exception as e:
            logger.error(f"Error getting Climate TRACE data for project: {e}")
            return None
    
    def _calculate_eligibility_score(self, project_data: Dict[str, Any], 
                                   ct_data: Optional[Dict[str, Any]], 
                                   verification_delta: Optional[float]) -> float:
        """Calculate project eligibility score"""
        try:
            score = 0.0
            
            # Base score for verification status
            verification_status = project_data.get('verification_status', 'pending')
            if verification_status == 'verified':
                score += 40.0
            elif verification_status == 'under_review':
                score += 20.0
            else:
                score += 5.0
            
            # Score for Climate TRACE alignment
            if ct_data:
                score += 30.0
                
                # Bonus for low verification delta
                if verification_delta is not None:
                    if abs(verification_delta) < 5:
                        score += 20.0
                    elif abs(verification_delta) < 15:
                        score += 10.0
                    elif abs(verification_delta) < 25:
                        score += 5.0
            
            # Score for credit availability
            available_credits = project_data.get('available_credits', 0)
            total_credits = project_data.get('total_credits', 1)
            availability_ratio = available_credits / total_credits if total_credits > 0 else 0
            
            if availability_ratio > 0.5:
                score += 10.0
            elif availability_ratio > 0.2:
                score += 5.0
            
            return min(score, 100.0)
            
        except Exception as e:
            logger.error(f"Error calculating eligibility score: {e}")
            return 0.0
    
    def get_market_prices(self, standard: str = 'VCS') -> List[MarketPrice]:
        """Get current market prices for carbon credits"""
        try:
            # This would integrate with real carbon market APIs
            # For now, return mock data with realistic price ranges
            
            mock_prices = {
                'VCS': [
                    MarketPrice(
                        standard='VCS',
                        project_type='forest_conservation',
                        price_per_ton=8.50,
                        currency='USD',
                        volume_available=1000000,
                        last_updated=datetime.now() - timedelta(hours=2)
                    ),
                    MarketPrice(
                        standard='VCS',
                        project_type='renewable_energy',
                        price_per_ton=12.75,
                        currency='USD',
                        volume_available=500000,
                        last_updated=datetime.now() - timedelta(hours=1)
                    )
                ],
                'GS': [
                    MarketPrice(
                        standard='Gold Standard',
                        project_type='renewable_energy',
                        price_per_ton=15.25,
                        currency='USD',
                        volume_available=300000,
                        last_updated=datetime.now() - timedelta(minutes=30)
                    ),
                    MarketPrice(
                        standard='Gold Standard',
                        project_type='cookstove',
                        price_per_ton=18.50,
                        currency='USD',
                        volume_available=200000,
                        last_updated=datetime.now() - timedelta(minutes=15)
                    )
                ]
            }
            
            return mock_prices.get(standard, [])
            
        except Exception as e:
            logger.error(f"Error getting market prices: {e}")
            return []
    
    def calculate_portfolio_value(self, portfolio: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate total portfolio value and metrics"""
        try:
            total_credits = 0
            total_value = 0.0
            standard_breakdown = {}
            type_breakdown = {}
            
            for holding in portfolio:
                credits = holding.get('credits', 0)
                price = holding.get('price_per_ton', 0)
                standard = holding.get('standard', 'Unknown')
                project_type = holding.get('project_type', 'Unknown')
                
                total_credits += credits
                total_value += credits * price
                
                # Breakdown by standard
                if standard not in standard_breakdown:
                    standard_breakdown[standard] = {'credits': 0, 'value': 0.0}
                standard_breakdown[standard]['credits'] += credits
                standard_breakdown[standard]['value'] += credits * price
                
                # Breakdown by project type
                if project_type not in type_breakdown:
                    type_breakdown[project_type] = {'credits': 0, 'value': 0.0}
                type_breakdown[project_type]['credits'] += credits
                type_breakdown[project_type]['value'] += credits * price
            
            return {
                'total_credits': total_credits,
                'total_value_usd': round(total_value, 2),
                'average_price_per_ton': round(total_value / total_credits, 2) if total_credits > 0 else 0,
                'standard_breakdown': standard_breakdown,
                'type_breakdown': type_breakdown,
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio value: {e}")
            return {
                'error': str(e),
                'calculated_at': datetime.now().isoformat()
            }
    
    def generate_carbon_markets_dashboard(self, organization_emissions: Dict[str, Any]) -> Dict[str, Any]:
        """Generate carbon markets dashboard data"""
        try:
            # Calculate total organization emissions
            total_emissions = sum(organization_emissions.values()) if organization_emissions else 0
            
            # Get market prices for different standards
            vcs_prices = self.get_market_prices('VCS')
            gs_prices = self.get_market_prices('GS')
            
            # Calculate offset potential
            offset_potential = {
                'total_emissions_tonnes': total_emissions / 1000,  # Convert kg to tonnes
                'recommended_offset_percentage': 10,  # 10% offset recommendation
                'recommended_offset_tonnes': (total_emissions / 1000) * 0.1,
                'estimated_cost_range': {
                    'min_cost_usd': (total_emissions / 1000) * 0.1 * 5.0,  # $5/tonne minimum
                    'max_cost_usd': (total_emissions / 1000) * 0.1 * 25.0,  # $25/tonne maximum
                    'average_cost_usd': (total_emissions / 1000) * 0.1 * 15.0  # $15/tonne average
                }
            }
            
            # Market overview
            market_overview = {
                'total_standards': len(self.carbon_standards),
                'active_projects': 150,  # Mock data
                'total_credits_available': 5000000,  # Mock data
                'average_price_per_ton': 15.0,
                'price_trend': 'stable',  # Mock data
                'market_confidence': 'high'
            }
            
            # Top project recommendations
            project_recommendations = [
                {
                    'project_type': 'renewable_energy',
                    'standard': 'VCS',
                    'price_per_ton': 12.75,
                    'credits_available': 500000,
                    'eligibility_score': 0.95,
                    'description': 'Solar and wind energy projects in developing countries'
                },
                {
                    'project_type': 'forest_conservation',
                    'standard': 'VCS',
                    'price_per_ton': 8.50,
                    'credits_available': 1000000,
                    'eligibility_score': 0.90,
                    'description': 'Forest conservation and REDD+ projects'
                },
                {
                    'project_type': 'renewable_energy',
                    'standard': 'Gold Standard',
                    'price_per_ton': 15.25,
                    'credits_available': 300000,
                    'eligibility_score': 0.88,
                    'description': 'High-quality renewable energy projects with co-benefits'
                }
            ]
            
            # Sector-specific recommendations
            sector_recommendations = {}
            for sector, emissions in organization_emissions.items():
                if emissions > 0:
                    # Map organization sectors to carbon project types
                    if sector.lower() in ['power', 'electricity']:
                        project_type = 'renewable_energy'
                    elif sector.lower() in ['transportation', 'shipping']:
                        project_type = 'transportation'
                    elif sector.lower() in ['manufacturing', 'steel', 'cement']:
                        project_type = 'waste_management'
                    else:
                        project_type = 'forest_conservation'
                    
                    sector_recommendations[sector] = {
                        'emissions_tonnes': emissions / 1000,
                        'recommended_project_type': project_type,
                        'estimated_offset_cost': (emissions / 1000) * 0.1 * 15.0,
                        'priority': 'high' if emissions > 10000 else 'medium'
                    }
            
            return {
                'offset_potential': offset_potential,
                'market_overview': market_overview,
                'project_recommendations': project_recommendations,
                'sector_recommendations': sector_recommendations,
                'market_prices': {
                    'vcs': [{'project_type': p.project_type, 'price_per_ton': p.price_per_ton, 'volume_available': p.volume_available} for p in vcs_prices],
                    'gold_standard': [{'project_type': p.project_type, 'price_per_ton': p.price_per_ton, 'volume_available': p.volume_available} for p in gs_prices]
                },
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating carbon markets dashboard: {e}")
            return {
                'error': str(e),
                'last_updated': datetime.now().isoformat()
            }