"""
Enhanced Climate TRACE integration service combining API and methodology approaches
"""
import os
import logging
import requests
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
import hashlib
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from pathlib import Path

from ..models import EmissionRecord, ClimateTraceCrosscheck
from .climate_trace import ClimateTraceService, CT_ENABLED

logger = logging.getLogger(__name__)

class EnhancedClimateTraceService(ClimateTraceService):
    """
    Enhanced Climate TRACE service that combines API access with methodology documents
    """
    
    def __init__(self):
        super().__init__()
        self.methodology_cache = {}
        self.enhanced_emission_factors = {}
        self.methodology_base_url = "https://raw.githubusercontent.com/climatetracecoalition/methodology-documents/main"
        self.cache_dir = Path("cache/climate_trace")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load enhanced emission factors
        self._load_enhanced_emission_factors()
    
    def _load_default_enhanced_factors(self):
        """Load default enhanced emission factors when methodology documents are not available"""
        try:
            logger.info("Loading default enhanced emission factors...")
            
            # Load all default factors for all sectors
            default_sectors = ['power', 'oil_and_gas', 'transportation', 'manufacturing', 'waste', 'agriculture']
            
            for sector in default_sectors:
                self.enhanced_emission_factors[sector] = self._get_enhanced_default_factors(sector)
            
            # Save to cache for future use
            self._save_enhanced_emission_factors()
            
            logger.info(f"Loaded default enhanced factors for {len(self.enhanced_emission_factors)} sectors")
            
        except Exception as e:
            logger.error(f"Error loading default enhanced factors: {e}")
            self.enhanced_emission_factors = {}
    
    def _load_enhanced_emission_factors(self):
        """Load enhanced emission factors from Climate TRACE methodologies"""
        try:
            # Load from local cache first
            cache_file = self.cache_dir / "enhanced_emission_factors.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    self.enhanced_emission_factors = json.load(f)
                logger.info("Loaded enhanced emission factors from cache")
                return
            
            # If no cache, try to fetch from methodology documents
            logger.info("No cache found, attempting to fetch methodology documents...")
            self._fetch_methodology_documents()
            
            # If still no factors loaded, use default enhanced factors
            if not self.enhanced_emission_factors:
                logger.info("No methodology data available, loading default enhanced factors...")
                self._load_default_enhanced_factors()
            
        except Exception as e:
            logger.error(f"Error loading enhanced emission factors: {e}")
            logger.info("Falling back to default enhanced factors...")
            self._load_default_enhanced_factors()
    
    def _fetch_methodology_documents(self):
        """Fetch and parse Climate TRACE methodology documents"""
        try:
            logger.info("Attempting to fetch Climate TRACE methodology documents...")
            
            # Try to fetch the 2025 changelog
            changelog_url = f"{self.methodology_base_url}/2025/CHANGELOG.md"
            logger.info(f"Fetching changelog from: {changelog_url}")
            
            response = requests.get(changelog_url, timeout=10)
            
            if response.status_code == 200:
                changelog_content = response.text
                logger.info("Successfully fetched Climate TRACE methodology changelog")
                self._parse_changelog(changelog_content)
            else:
                logger.warning(f"Could not fetch changelog: HTTP {response.status_code}")
                logger.info("Will use default enhanced factors instead")
                
        except requests.exceptions.Timeout:
            logger.warning("Timeout fetching methodology documents - will use default factors")
        except requests.exceptions.ConnectionError:
            logger.warning("Connection error fetching methodology documents - will use default factors")
        except Exception as e:
            logger.error(f"Error fetching methodology documents: {e}")
            logger.info("Will use default enhanced factors instead")
    
    def _parse_changelog(self, changelog_content: str):
        """Parse the changelog to extract methodology updates"""
        try:
            logger.info("Parsing changelog for sector updates...")
            
            # Extract sector updates from changelog
            sectors_updated = []
            lines = changelog_content.split('\n')
            
            for line in lines:
                if '##' in line and any(sector in line.lower() for sector in 
                    ['power', 'oil', 'gas', 'transportation', 'manufacturing', 'waste', 'agriculture']):
                    sectors_updated.append(line.strip())
            
            logger.info(f"Found {len(sectors_updated)} sector updates in changelog")
            
            # For each updated sector, fetch the methodology document
            for sector_line in sectors_updated:
                sector = self._extract_sector_from_line(sector_line)
                if sector:
                    logger.info(f"Fetching methodology for sector: {sector}")
                    self._fetch_sector_methodology(sector)
            
            # If we got some factors, save them to cache
            if self.enhanced_emission_factors:
                self._save_enhanced_emission_factors()
                logger.info(f"Saved {len(self.enhanced_emission_factors)} sectors to cache")
            else:
                logger.info("No emission factors extracted from methodology documents")
            
        except Exception as e:
            logger.error(f"Error parsing changelog: {e}")
    
    def _extract_sector_from_line(self, line: str) -> Optional[str]:
        """Extract sector name from changelog line"""
        line_lower = line.lower()
        if 'power' in line_lower or 'electricity' in line_lower:
            return 'power'
        elif 'oil' in line_lower or 'gas' in line_lower:
            return 'oil_and_gas'
        elif 'transportation' in line_lower or 'transport' in line_lower:
            return 'transportation'
        elif 'manufacturing' in line_lower:
            return 'manufacturing'
        elif 'waste' in line_lower:
            return 'waste'
        elif 'agriculture' in line_lower:
            return 'agriculture'
        return None
    
    def _fetch_sector_methodology(self, sector: str):
        """Fetch methodology document for a specific sector"""
        try:
            # Map sector to methodology document path
            sector_paths = {
                'power': '2025/sectors/power-generation',
                'oil_and_gas': '2025/sectors/oil-and-gas',
                'transportation': '2025/sectors/transportation',
                'manufacturing': '2025/sectors/manufacturing',
                'waste': '2025/sectors/waste',
                'agriculture': '2025/sectors/agriculture'
            }
            
            if sector not in sector_paths:
                logger.warning(f"No methodology path defined for sector: {sector}")
                self._add_generic_emission_factors(sector)
                return
            
            # Try to fetch the methodology document
            methodology_url = f"{self.methodology_base_url}/{sector_paths[sector]}/methodology.md"
            logger.info(f"Fetching methodology from: {methodology_url}")
            
            response = requests.get(methodology_url, timeout=10)
            
            if response.status_code == 200:
                methodology_content = response.text
                self._parse_sector_methodology(sector, methodology_content)
                logger.info(f"Successfully fetched and parsed methodology for {sector}")
            else:
                logger.warning(f"Could not fetch methodology for {sector}: HTTP {response.status_code}")
                # Fallback to generic emission factors
                self._add_generic_emission_factors(sector)
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching methodology for {sector} - using default factors")
            self._add_generic_emission_factors(sector)
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error fetching methodology for {sector} - using default factors")
            self._add_generic_emission_factors(sector)
        except Exception as e:
            logger.error(f"Error fetching methodology for {sector}: {e}")
            self._add_generic_emission_factors(sector)
    
    def _parse_sector_methodology(self, sector: str, methodology_content: str):
        """Parse sector methodology to extract emission factors"""
        try:
            # Extract emission factors from methodology document
            emission_factors = {}
            
            # Look for emission factor tables or specifications
            lines = methodology_content.split('\n')
            in_emission_section = False
            
            for line in lines:
                line_lower = line.lower()
                
                # Check if we're in an emission factor section
                if 'emission factor' in line_lower or 'emissions factor' in line_lower:
                    in_emission_section = True
                    continue
                
                if in_emission_section:
                    # Parse emission factor data
                    if '|' in line and any(char.isdigit() for char in line):
                        # This looks like a table row with emission factors
                        parts = [part.strip() for part in line.split('|')]
                        if len(parts) >= 3:
                            try:
                                fuel_type = parts[0].lower()
                                factor_value = float(parts[1].replace(',', ''))
                                unit = parts[2] if len(parts) > 2 else 'kg CO2e/unit'
                                
                                emission_factors[fuel_type] = {
                                    'factor': factor_value,
                                    'unit': unit,
                                    'source': 'Climate TRACE Methodology',
                                    'sector': sector,
                                    'last_updated': datetime.now().isoformat()
                                }
                            except (ValueError, IndexError):
                                continue
                
                # Stop parsing if we hit another section
                if line.startswith('#') and in_emission_section:
                    break
            
            # If no emission factors found in methodology, use enhanced defaults
            if not emission_factors:
                emission_factors = self._get_enhanced_default_factors(sector)
            
            self.enhanced_emission_factors[sector] = emission_factors
            
        except Exception as e:
            logger.error(f"Error parsing methodology for {sector}: {e}")
            self._add_generic_emission_factors(sector)
    
    def _get_enhanced_default_factors(self, sector: str) -> Dict[str, Dict]:
        """Get enhanced default emission factors based on Climate TRACE standards"""
        enhanced_factors = {
            'power': {
                'coal': {'factor': 820.0, 'unit': 'kg CO2e/MWh', 'source': 'Climate TRACE Enhanced'},
                'natural_gas': {'factor': 490.0, 'unit': 'kg CO2e/MWh', 'source': 'Climate TRACE Enhanced'},
                'oil': {'factor': 778.0, 'unit': 'kg CO2e/MWh', 'source': 'Climate TRACE Enhanced'},
                'solar': {'factor': 41.0, 'unit': 'kg CO2e/MWh', 'source': 'Climate TRACE Enhanced'},
                'wind': {'factor': 11.0, 'unit': 'kg CO2e/MWh', 'source': 'Climate TRACE Enhanced'},
                'hydro': {'factor': 24.0, 'unit': 'kg CO2e/MWh', 'source': 'Climate TRACE Enhanced'},
                'nuclear': {'factor': 12.0, 'unit': 'kg CO2e/MWh', 'source': 'Climate TRACE Enhanced'}
            },
            'oil_and_gas': {
                'oil_production': {'factor': 0.5, 'unit': 'kg CO2e/barrel', 'source': 'Climate TRACE Enhanced'},
                'gas_production': {'factor': 0.3, 'unit': 'kg CO2e/m3', 'source': 'Climate TRACE Enhanced'},
                'refining': {'factor': 0.4, 'unit': 'kg CO2e/barrel', 'source': 'Climate TRACE Enhanced'}
            },
            'transportation': {
                'gasoline': {'factor': 2.31, 'unit': 'kg CO2e/liter', 'source': 'Climate TRACE Enhanced'},
                'diesel': {'factor': 2.68, 'unit': 'kg CO2e/liter', 'source': 'Climate TRACE Enhanced'},
                'aviation_fuel': {'factor': 3.15, 'unit': 'kg CO2e/liter', 'source': 'Climate TRACE Enhanced'},
                'shipping_fuel': {'factor': 3.2, 'unit': 'kg CO2e/liter', 'source': 'Climate TRACE Enhanced'}
            },
            'manufacturing': {
                'cement': {'factor': 0.9, 'unit': 'kg CO2e/kg', 'source': 'Climate TRACE Enhanced'},
                'steel': {'factor': 1.8, 'unit': 'kg CO2e/kg', 'source': 'Climate TRACE Enhanced'},
                'aluminum': {'factor': 8.2, 'unit': 'kg CO2e/kg', 'source': 'Climate TRACE Enhanced'},
                'chemicals': {'factor': 2.1, 'unit': 'kg CO2e/kg', 'source': 'Climate TRACE Enhanced'}
            },
            'waste': {
                'landfill': {'factor': 0.3, 'unit': 'kg CO2e/kg', 'source': 'Climate TRACE Enhanced'},
                'wastewater': {'factor': 0.1, 'unit': 'kg CO2e/m3', 'source': 'Climate TRACE Enhanced'},
                'incineration': {'factor': 0.8, 'unit': 'kg CO2e/kg', 'source': 'Climate TRACE Enhanced'}
            },
            'agriculture': {
                'livestock': {'factor': 2.5, 'unit': 'kg CO2e/kg', 'source': 'Climate TRACE Enhanced'},
                'rice': {'factor': 0.4, 'unit': 'kg CO2e/kg', 'source': 'Climate TRACE Enhanced'},
                'crops': {'factor': 0.2, 'unit': 'kg CO2e/kg', 'source': 'Climate TRACE Enhanced'}
            }
        }
        
        return enhanced_factors.get(sector, {})
    
    def _add_generic_emission_factors(self, sector: str):
        """Add generic emission factors for a sector"""
        self.enhanced_emission_factors[sector] = self._get_enhanced_default_factors(sector)
    
    def _save_enhanced_emission_factors(self):
        """Save enhanced emission factors to cache"""
        try:
            cache_file = self.cache_dir / "enhanced_emission_factors.json"
            with open(cache_file, 'w') as f:
                json.dump(self.enhanced_emission_factors, f, indent=2)
            logger.info("Saved enhanced emission factors to cache")
        except Exception as e:
            logger.error(f"Error saving enhanced emission factors: {e}")
    
    def get_enhanced_emission_factor(self, sector: str, fuel_type: str, 
                                   activity_type: str = None) -> Optional[Dict]:
        """
        Get enhanced emission factor from Climate TRACE methodologies
        
        Args:
            sector: Sector (power, oil_and_gas, transportation, etc.)
            fuel_type: Fuel type (coal, natural_gas, etc.)
            activity_type: Activity type for additional context
            
        Returns:
            Dictionary with emission factor data or None
        """
        try:
            # Normalize inputs - handle None values
            if sector is None:
                sector = 'other'
            if fuel_type is None:
                fuel_type = 'other'
            
            sector = sector.lower().replace(' ', '_')
            fuel_type = fuel_type.lower().replace(' ', '_')
            
            # Check if we have enhanced factors for this sector
            if sector in self.enhanced_emission_factors:
                sector_factors = self.enhanced_emission_factors[sector]
                
                # Try exact match first
                if fuel_type in sector_factors:
                    return sector_factors[fuel_type]
                
                # Try partial matches
                for factor_fuel, factor_data in sector_factors.items():
                    if fuel_type in factor_fuel or factor_fuel in fuel_type:
                        return factor_data
            
            # No fallback available - return None
            return None
            
        except Exception as e:
            logger.error(f"Error getting enhanced emission factor: {e}")
            return None
    
    def calculate_enhanced_emissions(self, record: Dict) -> Dict:
        """
        Calculate emissions using enhanced Climate TRACE methodologies
        
        Args:
            record: Emission record dictionary
            
        Returns:
            Dictionary with enhanced emission calculations
        """
        try:
            # Get basic emissions calculation
            basic_result = super().calculate_enhanced_emissions(record) if hasattr(super(), 'calculate_enhanced_emissions') else {}
            
            # Get enhanced emission factor
            sector = record.get('ct_sector', 'other')
            fuel_type = record.get('fuel_type', 'other')
            activity_type = record.get('activity_type', 'other')
            
            enhanced_factor = self.get_enhanced_emission_factor(sector, fuel_type, activity_type)
            
            # If no specific factor found, try to use a default factor for the sector
            if not enhanced_factor and sector in self.enhanced_emission_factors:
                sector_factors = self.enhanced_emission_factors[sector]
                if sector_factors:
                    # Use the first available factor as a default
                    first_factor_key = list(sector_factors.keys())[0]
                    enhanced_factor = sector_factors[first_factor_key]
                    logger.info(f"Using default factor '{first_factor_key}' for sector '{sector}'")
            
            if enhanced_factor:
                # Calculate emissions with enhanced factor
                activity_amount = float(record.get('activity_amount', 0))
                factor_value = enhanced_factor['factor']
                unit = enhanced_factor['unit']
                
                enhanced_emissions = activity_amount * factor_value
                
                return {
                    **basic_result,
                    'enhanced_emissions_kgco2e': enhanced_emissions,
                    'enhanced_emission_factor_value': factor_value,
                    'enhanced_emission_factor_unit': unit,
                    'enhanced_factor_source': enhanced_factor['source'],
                    'methodology_used': 'Climate TRACE Enhanced',
                    'confidence_score': 0.90  # Slightly lower confidence when using default factor
                }
            
            return basic_result
            
        except Exception as e:
            logger.error(f"Error calculating enhanced emissions: {e}")
            return basic_result if 'basic_result' in locals() else {}
    
    def validate_against_methodology(self, record: Dict) -> Dict:
        """
        Validate emission record against Climate TRACE methodologies
        
        Args:
            record: Emission record dictionary
            
        Returns:
            Dictionary with validation results
        """
        try:
            validation_result = {
                'is_valid': True,
                'confidence_score': 1.0,
                'validation_issues': [],
                'methodology_compliance': 'compliant',
                'suggestions': []
            }
            
            # Check if we have enhanced factors for this sector
            sector = record.get('ct_sector', 'other')
            if sector in self.enhanced_emission_factors:
                validation_result['methodology_compliance'] = 'enhanced'
                validation_result['confidence_score'] = 0.95
            else:
                validation_result['methodology_compliance'] = 'basic'
                validation_result['confidence_score'] = 0.8
                validation_result['suggestions'].append(
                    f"Consider using Climate TRACE methodology for {sector} sector"
                )
            
            # Check emission factor accuracy
            fuel_type = record.get('fuel_type', 'other')
            enhanced_factor = self.get_enhanced_emission_factor(sector, fuel_type)
            
            if enhanced_factor:
                current_factor = record.get('emission_factor_value', 0)
                if current_factor > 0:
                    factor_diff = abs(current_factor - enhanced_factor['factor']) / enhanced_factor['factor']
                    if factor_diff > 0.1:  # 10% difference
                        validation_result['validation_issues'].append(
                            f"Emission factor differs by {factor_diff*100:.1f}% from Climate TRACE methodology"
                        )
                        validation_result['confidence_score'] *= 0.9
            
            # Check data completeness
            required_fields = ['activity_amount', 'fuel_type', 'ct_sector']
            missing_fields = [field for field in required_fields if not record.get(field)]
            
            if missing_fields:
                validation_result['validation_issues'].append(
                    f"Missing required fields: {', '.join(missing_fields)}"
                )
                validation_result['confidence_score'] *= 0.8
            
            # Overall validation
            if validation_result['validation_issues']:
                validation_result['is_valid'] = False
                validation_result['methodology_compliance'] = 'needs_review'
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating against methodology: {e}")
            return {
                'is_valid': False,
                'confidence_score': 0.0,
                'validation_issues': [f"Validation error: {str(e)}"],
                'methodology_compliance': 'error',
                'suggestions': ['Review data quality and try again']
            }
    
    def get_methodology_summary(self) -> Dict:
        """Get summary of available methodologies and emission factors"""
        try:
            summary = {
                'total_sectors': len(self.enhanced_emission_factors),
                'sectors': {},
                'last_updated': datetime.now().isoformat(),
                'methodology_source': 'Climate TRACE Enhanced'
            }
            
            for sector, factors in self.enhanced_emission_factors.items():
                summary['sectors'][sector] = {
                    'fuel_types': list(factors.keys()),
                    'factor_count': len(factors),
                    'source': factors[list(factors.keys())[0]]['source'] if factors else 'Unknown'
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting methodology summary: {e}")
            return {
                'total_sectors': 0,
                'sectors': {},
                'last_updated': datetime.now().isoformat(),
                'methodology_source': 'Error',
                'error': str(e)
            }
    
    def get_available_sectors(self) -> List[Dict]:
        """Get list of available sectors with their details"""
        try:
            sectors = []
            for sector, factors in self.enhanced_emission_factors.items():
                sector_info = {
                    'name': sector,
                    'display_name': sector.replace('_', ' ').title(),
                    'fuel_types': list(factors.keys()),
                    'factor_count': len(factors),
                    'source': factors[list(factors.keys())[0]]['source'] if factors else 'Unknown'
                }
                sectors.append(sector_info)
            
            return sectors
            
        except Exception as e:
            logger.error(f"Error getting available sectors: {e}")
            return []


# Global enhanced service instance
enhanced_climate_trace_service = EnhancedClimateTraceService()
