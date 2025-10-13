"""
Simplified Climate TRACE Integration Service

This service provides Climate TRACE methodology-based emission estimates
for businesses to compare against their own reported emissions.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models import EmissionRecord, ClimateTraceCrosscheck

logger = logging.getLogger(__name__)

class ClimateTraceService:
    """Service for providing Climate TRACE methodology-based emission estimates"""
    
    def __init__(self):
        self.enabled = os.getenv('COMPLIANCE_CT_ENABLED', 'false').lower() == 'true'
        
        # Climate TRACE methodology-based emission factors (kg CO2e per unit)
        self.emission_factors = {
            'electricity-generation': {
                'coal': 0.9,      # kg CO2e per kWh
                'natural-gas': 0.4,
                'oil': 0.7,
                'renewable': 0.05,
                'default': 0.5
            },
            'road-transportation': {
                'gasoline': 0.2,  # kg CO2e per km
                'diesel': 0.15,
                'electric': 0.05,
                'default': 0.18
            },
            'iron-and-steel': {
                'default': 1.8    # kg CO2e per kg steel
            },
            'oil-and-gas-production': {
                'default': 0.1    # kg CO2e per MJ
            },
            'buildings': {
                'heating': 0.05,  # kg CO2e per m²
                'cooling': 0.03,
                'lighting': 0.02,
                'default': 0.04
            },
            'aviation': {
                'default': 0.3    # kg CO2e per passenger-km
            },
            'shipping': {
                'default': 0.01   # kg CO2e per tonne-km
            },
            'manufacturing': {
                'default': 0.3    # kg CO2e per unit
            },
            'agriculture': {
                'default': 0.1    # kg CO2e per kg
            },
            'waste': {
                'default': 0.2    # kg CO2e per kg
            }
        }
        
        # Typical activity levels for benchmarking (per month)
        self.benchmark_activity_levels = {
            'electricity-generation': 100000,  # kWh
            'road-transportation': 50000,      # km
            'iron-and-steel': 10000,           # kg
            'oil-and-gas-production': 100000,  # MJ
            'buildings': 10000,                # m²
            'aviation': 20000,                 # passenger-km
            'shipping': 50000,                 # tonne-km
            'manufacturing': 20000,            # units
            'agriculture': 50000,              # kg
            'waste': 30000                     # kg
        }
        
        logger.info(f"Climate TRACE service initialized - Enabled: {self.enabled}")
    
    def map_activity_to_climate_trace(self, activity_type: str, 
                                     fuel_type: Optional[str] = None,
                                     category: Optional[str] = None) -> Dict[str, str]:
        """
        Map internal activity type to Climate TRACE sector
        
        Args:
            activity_type: Internal activity type
            fuel_type: Optional fuel type
            category: Optional category
            
        Returns:
            Dictionary with Climate TRACE mapping
        """
        if not self.enabled:
            return {
                'ct_sector': None,
                'ct_subsector': None,
                'ct_asset_type': None,
                'ct_region': 'Global',
                'ct_country_code': None
            }
        
        activity_lower = activity_type.lower() if activity_type else ''
        fuel_lower = fuel_type.lower() if fuel_type else ''
        category_lower = category.lower() if category else ''
        
        # Enhanced mapping logic - check both activity_type and category
        if (any(keyword in activity_lower for keyword in ['electricity', 'power', 'generation']) or
            any(keyword in category_lower for keyword in ['electricity', 'power', 'generation'])):
            return {
                'ct_sector': 'electricity-generation',
                'ct_subsector': 'Fossil Fuels' if any(f in fuel_lower for f in ['coal', 'gas', 'oil']) else 'Renewables',
                'ct_asset_type': 'Power Plant',
                'ct_region': 'Global',
                'ct_country_code': None
            }
        elif any(keyword in activity_lower for keyword in ['transport', 'vehicle', 'road', 'truck', 'car']):
            return {
                'ct_sector': 'road-transportation',
                'ct_subsector': 'Passenger Vehicles' if 'passenger' in activity_lower else 'Freight',
                'ct_asset_type': 'Vehicle',
                'ct_region': 'Global',
                'ct_country_code': None
            }
        elif any(keyword in activity_lower for keyword in ['industrial', 'process', 'manufacturing', 'steel', 'iron']):
            return {
                'ct_sector': 'iron-and-steel',
                'ct_subsector': 'Steel Production',
                'ct_asset_type': 'Industrial Facility',
                'ct_region': 'Global',
                'ct_country_code': None
            }
        elif any(keyword in activity_lower for keyword in ['building', 'office', 'residential', 'commercial']):
            return {
                'ct_sector': 'buildings',
                'ct_subsector': 'Commercial' if 'commercial' in activity_lower else 'Residential',
                'ct_asset_type': 'Building',
                'ct_region': 'Global',
                'ct_country_code': None
            }
        elif (any(keyword in activity_lower for keyword in ['waste', 'landfill', 'disposal']) or
              any(keyword in category_lower for keyword in ['waste', 'landfill', 'disposal'])):
            return {
                'ct_sector': 'waste',
                'ct_subsector': 'Waste Management',
                'ct_asset_type': 'Waste Facility',
                'ct_region': 'Global',
                'ct_country_code': None
            }
        elif any(keyword in activity_lower for keyword in ['aviation', 'aircraft', 'flight']):
            return {
                'ct_sector': 'aviation',
                'ct_subsector': 'Passenger Aviation',
                'ct_asset_type': 'Aircraft',
                'ct_region': 'Global',
                'ct_country_code': None
            }
        elif any(keyword in activity_lower for keyword in ['shipping', 'vessel', 'maritime']):
            return {
                'ct_sector': 'shipping',
                'ct_subsector': 'Cargo Shipping',
                'ct_asset_type': 'Vessel',
                'ct_region': 'Global',
                'ct_country_code': None
            }
        elif any(keyword in activity_lower for keyword in ['oil', 'gas', 'petroleum']):
            return {
                'ct_sector': 'oil-and-gas-production',
                'ct_subsector': 'Oil Production' if 'oil' in activity_lower else 'Gas Production',
                'ct_asset_type': 'Oil/Gas Facility',
                'ct_region': 'Global',
                'ct_country_code': None
            }
        else:
            return {
                'ct_sector': 'other',
                'ct_subsector': 'Other',
                'ct_asset_type': 'Other Asset',
                'ct_region': 'Global',
                'ct_country_code': None
            }
    
    def estimate_climate_trace_emissions(self, sector: str, activity_level: float, 
                                       fuel_type: Optional[str] = None) -> float:
        """
        Estimate emissions using Climate TRACE methodology
        
        Args:
            sector: Climate TRACE sector
            activity_level: Activity level (e.g., kWh, km, kg)
            fuel_type: Optional fuel type for more accurate estimates
            
        Returns:
            Estimated emissions in kg CO2e
        """
        if not self.enabled or sector not in self.emission_factors:
            return 0.0
        
        # Get emission factor for the sector and fuel type
        sector_factors = self.emission_factors[sector]
        if fuel_type and fuel_type.lower() in sector_factors:
            emission_factor = sector_factors[fuel_type.lower()]
        else:
            emission_factor = sector_factors.get('default', 0.1)
        
        return activity_level * emission_factor
    
    def get_benchmark_emissions(self, sector: str) -> Dict[str, Any]:
        """
        Get Climate TRACE benchmark emissions for a sector
        
        Args:
            sector: Climate TRACE sector
            
        Returns:
            Dictionary with benchmark data
        """
        if not self.enabled or sector not in self.benchmark_activity_levels:
            return {
                'sector': sector,
                'benchmark_emissions_kgco2e': 0,
                'benchmark_activity_level': 0,
                'emission_factor': 0,
                'confidence': 'low'
            }
        
        activity_level = self.benchmark_activity_levels[sector]
        emission_factor = self.emission_factors.get(sector, {}).get('default', 0.1)
        benchmark_emissions = activity_level * emission_factor
        
        return {
            'sector': sector,
            'benchmark_emissions_kgco2e': benchmark_emissions,
            'benchmark_activity_level': activity_level,
            'emission_factor': emission_factor,
            'confidence': 'medium'
        }
    
    def run_crosscheck_analysis(self, db: Session, year: int, month: int,
                               threshold_percentage: float = 10.0) -> List[ClimateTraceCrosscheck]:
        """
        Run cross-check analysis between business emissions and Climate TRACE benchmarks
        
        Args:
            db: Database session
            year: Year to analyze
            month: Month to analyze
            threshold_percentage: Threshold for compliance flagging
            
        Returns:
            List of cross-check results
        """
        if not self.enabled:
            logger.warning("Climate TRACE integration disabled")
            return []
        
        try:
            # Get business emissions by sector
            our_emissions = self._get_our_emissions_by_sector(db, year, month)
            
            # Run comparisons with Climate TRACE benchmarks
            crosschecks = []
            for sector, our_data in our_emissions.items():
                # Get Climate TRACE benchmark for this sector
                benchmark = self.get_benchmark_emissions(sector)
                ct_emissions = benchmark['benchmark_emissions_kgco2e']
                
                # Aggregate our emissions by sector
                our_total_emissions = sum(our_data.values())
                
                if our_total_emissions > 0 or ct_emissions > 0:
                    # Calculate delta
                    delta = float(our_total_emissions - ct_emissions)
                    delta_pct = (delta / ct_emissions * 100) if ct_emissions > 0 else 0
                    
                    # Cap delta percentage to prevent database overflow
                    delta_pct = max(-9999.99, min(9999.99, delta_pct))
                    
                    # Determine compliance status
                    threshold_exceeded = abs(delta_pct) > threshold_percentage
                    compliance_status = self._determine_compliance_status(delta_pct, threshold_percentage)
                    
                    # Create crosscheck record
                    crosscheck = ClimateTraceCrosscheck(
                        year=year,
                        month=month,
                        ct_sector=sector,
                        ct_subsector=sector,
                        ct_emissions_kgco2e=Decimal(str(ct_emissions)),
                        our_emissions_kgco2e=Decimal(str(our_total_emissions)),
                        delta_kgco2e=Decimal(str(delta)),
                        delta_percentage=delta_pct,
                        compliance_status=compliance_status,
                        threshold_exceeded=threshold_exceeded,
                        created_at=datetime.now()
                    )
                    
                    db.add(crosscheck)
                    crosschecks.append(crosscheck)
            
            db.commit()
            logger.info(f"Created {len(crosschecks)} cross-check results for {year}-{month:02d}")
            return crosschecks
            
        except Exception as e:
            logger.error(f"Error running cross-check analysis: {e}")
            db.rollback()
            return []
    
    def _get_our_emissions_by_sector(self, db: Session, year: int, month: int) -> Dict:
        """Get business emissions aggregated by Climate TRACE sector"""
        try:
            # Query business emissions data
            query = text("""
                SELECT 
                    COALESCE(NULLIF(activity_type, 'None'), 'Unknown') as activity_type,
                    COALESCE(NULLIF(category, 'None'), 'Unknown') as category,
                    SUM(emissions_kgco2e) as total_emissions,
                    COUNT(*) as record_count
                FROM emission_records 
                WHERE EXTRACT(YEAR FROM date) = :year 
                AND EXTRACT(MONTH FROM date) = :month
                AND emissions_kgco2e IS NOT NULL 
                AND emissions_kgco2e > 0
                GROUP BY COALESCE(NULLIF(activity_type, 'None'), 'Unknown'), COALESCE(NULLIF(category, 'None'), 'Unknown')
            """)
            
            result = db.execute(query, {'year': year, 'month': month})
            results = {}
            
            for row in result:
                activity_type = row.activity_type or "Unknown"
                category = row.category or "Unknown"
                total_emissions = float(row.total_emissions or 0)
                record_count = row.record_count or 0
                
                # Map activity type and category to Climate TRACE sector
                mapping = self.map_activity_to_climate_trace(activity_type, category=category)
                sector = mapping['ct_sector'] or 'other'
                subsector = mapping['ct_subsector'] or 'other'
                
                if sector not in results:
                    results[sector] = {}
                
                # Aggregate by subsector
                if subsector not in results[sector]:
                    results[sector][subsector] = 0
                
                results[sector][subsector] += total_emissions
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting business emissions by sector: {e}")
            return {}
    
    def _determine_compliance_status(self, delta_percentage: float, 
                                   threshold_exceeded: bool) -> str:
        """Determine compliance status based on delta percentage"""
        if not threshold_exceeded:
            return "compliant"
        elif delta_percentage > 0:
            return "over_emitting"
        else:
            return "under_emitting"
    
    def map_records_to_climate_trace(self, db: Session, 
                                   record_ids: Optional[List[str]] = None) -> Dict:
        """
        Map existing emission records to Climate TRACE sectors
        
        Args:
            db: Database session
            record_ids: Optional list of specific record IDs to map
            
        Returns:
            Dictionary with mapping results
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'Climate TRACE integration disabled',
                'mapped_count': 0,
                'total_count': 0
            }
        
        try:
            # Get records to map
            query = db.query(EmissionRecord)
            if record_ids:
                query = query.filter(EmissionRecord.id.in_(record_ids))
            
            records = query.all()
            
            if not records:
                return {
                    'success': False,
                    'error': 'No records found to map',
                    'mapped_count': 0,
                    'total_count': 0
                }
            
            mapped_count = 0
            total_count = len(records)
            
            for record in records:
                try:
                    # Map to Climate TRACE taxonomy
                    mapping = self.map_activity_to_climate_trace(
                        record.activity_type,
                        getattr(record, 'fuel_type', None),
                        getattr(record, 'category', None)
                    )
                    
                    # Update record with Climate TRACE fields
                    record.ct_sector = mapping['ct_sector']
                    record.ct_subsector = mapping['ct_subsector']
                    record.ct_asset_type = mapping['ct_asset_type']
                    record.ct_region = mapping['ct_region']
                    record.ct_country_code = mapping['ct_country_code']
                    
                    mapped_count += 1
                    
                except Exception as e:
                    logger.warning(f"Error mapping record {record.id}: {e}")
                    continue
            
            db.commit()
            
            return {
                'success': True,
                'mapped_count': mapped_count,
                'total_count': total_count,
                'message': f'Successfully mapped {mapped_count}/{total_count} records to Climate TRACE sectors'
            }
            
        except Exception as e:
            logger.error(f"Error mapping records to Climate TRACE: {e}")
            db.rollback()
            return {
                'success': False,
                'error': str(e),
                'mapped_count': 0,
                'total_count': 0
            }
    
    def get_crosscheck_results(self, db: Session, year: Optional[int] = None, 
                              month: Optional[int] = None, 
                              compliance_status: Optional[str] = None) -> List[Dict]:
        """
        Get crosscheck results from the database
        
        Args:
            db: Database session
            year: Optional year filter
            month: Optional month filter
            compliance_status: Optional compliance status filter
            
        Returns:
            List of crosscheck results
        """
        if not self.enabled:
            return []
        
        try:
            query = db.query(ClimateTraceCrosscheck)
            
            if year:
                query = query.filter(ClimateTraceCrosscheck.year == year)
            if month:
                query = query.filter(ClimateTraceCrosscheck.month == month)
            if compliance_status:
                query = query.filter(ClimateTraceCrosscheck.compliance_status == compliance_status)
            
            crosschecks = query.order_by(ClimateTraceCrosscheck.created_at.desc()).limit(50).all()
            
            return [
                {
                    'id': str(crosscheck.id),
                    'year': crosscheck.year,
                    'month': crosscheck.month,
                    'sector': crosscheck.sector,
                    'our_emissions': float(crosscheck.our_emissions),
                    'climate_trace_estimate': float(crosscheck.climate_trace_estimate),
                    'delta_percentage': float(crosscheck.delta_percentage),
                    'compliance_status': crosscheck.compliance_status,
                    'threshold_exceeded': crosscheck.threshold_exceeded,
                    'created_at': crosscheck.created_at.isoformat() if crosscheck.created_at else None
                }
                for crosscheck in crosschecks
            ]
            
        except Exception as e:
            logger.error(f"Error getting crosscheck results: {e}")
            return []

# Global instance
climate_trace_service = ClimateTraceService()

# Export for backward compatibility
CT_ENABLED = climate_trace_service.enabled