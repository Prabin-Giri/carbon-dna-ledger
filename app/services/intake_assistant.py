"""
Intake Assistant service

Provides smart suggestions to minimize manual data entry by:
- Surfacing historical defaults from prior records (per supplier/activity)
- Suggesting Climate TRACE sector/subsector mapping for activity types
- Proposing reasonable defaults for units, market basis, and grid region
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import EmissionRecord
from .climate_trace import climate_trace_service


logger = logging.getLogger(__name__)


class IntakeAssistantService:
    """Encapsulates suggestion logic for intake forms and uploads."""

    def __init__(self, db: Session):
        self.db = db

    def suggest(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Return suggestions based on provided context.

        Expected payload keys (all optional):
        - supplier_name: str
        - activity_type: str
        - country_code: str
        - grid_region: str
        - scope: str|int
        - date: str (YYYY-MM-DD)
        """
        try:
            supplier_name = (payload.get("supplier_name") or "").strip()
            activity_type = (payload.get("activity_type") or "").strip().lower()
            country_code = (payload.get("country_code") or "").strip().upper()
            # CT-aligned optional filters
            sector = (payload.get("sector") or "").strip()
            subsector = (payload.get("subsector") or "").strip()
            year = payload.get("year")
            owner = (payload.get("owner") or "").strip()
            latitude = payload.get("latitude")
            longitude = payload.get("longitude")
            # Internal defaults (not used for CT matching)
            grid_region = (payload.get("grid_region") or "").strip()
            scope = payload.get("scope")

            suggestions: Dict[str, Any] = {
                "source": {
                    "history": False,
                    "climate_trace": False,
                },
                "history": {},
                "climate_trace": {},
                "defaults": {},
            }

            # 1) Historical defaults (most recent record for supplier)
            if supplier_name:
                record = (
                    self.db.query(EmissionRecord)
                    .filter(EmissionRecord.supplier_name == supplier_name)
                    .order_by(EmissionRecord.created_at.desc())
                    .first()
                )
                if record:
                    suggestions["history"] = {
                        "category": record.category,
                        "subcategory": record.subcategory,
                        "activity_type": record.activity_type,
                        "activity_unit": record.activity_unit,
                        "grid_region": record.grid_region,
                        "market_basis": record.market_basis,
                        "ef_source": record.ef_source,
                        "ef_ref_code": record.ef_ref_code,
                        "ef_version": record.ef_version,
                        "gwp_set": record.gwp_set,
                        "scope": record.scope,
                    }
                    suggestions["source"]["history"] = True

            # 2) Climate TRACE mapping and data fetching
            if activity_type or sector:
                try:
                    # Use provided sector or map from activity_type
                    ct_sector = sector or None
                    if not ct_sector and activity_type:
                        mapping = climate_trace_service.ACTIVITY_TO_CT_MAPPING
                        mapped = mapping.get(activity_type)
                        if mapped:
                            ct_sector = mapped.get("sector")
                    
                    if ct_sector:
                        # Fetch actual Climate TRACE data
                        ct_year = year or 2024  # Default to current year
                        ct_data = climate_trace_service.fetch_ct_monthly_data(
                            year=ct_year,
                            month=1,  # Default to January
                            sector=ct_sector,
                            country_code=country_code,
                            supplier_name=supplier_name
                        )
                        
                        # Process the CT data to extract relevant emission info
                        emission_data = []
                        total_emissions = 0
                        asset_count = 0
                        
                        if ct_data:
                            for record in ct_data:
                                if record.get("sector") == ct_sector:
                                    emissions = record.get("total_emissions_kgco2e", 0)
                                    if emissions:
                                        total_emissions += float(emissions)
                                        asset_count += 1
                                        
                                        emission_data.append({
                                            "sector": record.get("sector"),
                                            "emissions_kgco2e": emissions,
                                            "asset_count": record.get("asset_count", 1),
                                            "confidence": record.get("confidence", "unknown"),
                                            "year": record.get("year", ct_year),
                                            "month": record.get("month", 1)
                                        })
                        
                        suggestions["climate_trace"] = {
                            "ct_sector": ct_sector,
                            "ct_subsector": subsector or None,
                            "ct_country_code": country_code or None,
                            "ct_year": ct_year,
                            "ct_owner": owner or None,
                            "lat": latitude,
                            "lon": longitude,
                            # Actual emission data from Climate TRACE
                            "emission_data": emission_data,
                            "total_emissions_kgco2e": total_emissions,
                            "asset_count": asset_count,
                            "data_source": "Climate TRACE API" if ct_data else "No data found",
                            # Enhanced comparison and import features
                            "data_freshness": f"~60 days old (monthly updates)",
                            "confidence_level": "High (satellite + AI verified)" if ct_data else "Unknown",
                            "import_ready": bool(ct_data and total_emissions > 0),
                            "comparison_metrics": {
                                "avg_emissions_per_asset": total_emissions / max(asset_count, 1),
                                "sector_benchmark": total_emissions,
                                "data_quality": "Satellite + AI verified" if ct_data else "No data"
                            }
                        }
                        suggestions["source"]["climate_trace"] = True
                        
                except Exception as e:
                    logger.warning(f"CT data fetching failed: {e}")
                    # Fallback to just mapping without data
                    if activity_type:
                        mapping = climate_trace_service.ACTIVITY_TO_CT_MAPPING
                        mapped = mapping.get(activity_type)
                        if mapped:
                            suggestions["climate_trace"] = {
                                "ct_sector": mapped.get("sector"),
                                "ct_subsector": subsector or None,
                                "ct_country_code": country_code or None,
                                "ct_year": year,
                                "ct_owner": owner or None,
                                "lat": latitude,
                                "lon": longitude,
                                "data_source": "Mapping only (API error)",
                                "error": str(e)
                            }
                            suggestions["source"]["climate_trace"] = True

            # 3) Reasonable defaults
            if (grid_region or country_code) and (scope in (2, "2", "scope2", "Scope 2")):
                suggestions["defaults"]["market_basis"] = suggestions["history"].get("market_basis") or "location-based"
            if country_code and not grid_region and (scope in (2, "2", "scope2", "Scope 2")):
                # naive region hint; UI should let user refine
                suggestions["defaults"]["grid_region_hint"] = country_code

            return suggestions
        except Exception as e:
            logger.error(f"Error generating intake suggestions: {e}")
            return {"error": str(e)}


def build_intake_assistant(db: Session) -> IntakeAssistantService:
    return IntakeAssistantService(db)


