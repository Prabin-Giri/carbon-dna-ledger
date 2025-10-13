"""
Data ingestion services for CSV and PDF parsing
"""
import csv
import io
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import pandas as pd
import pdfplumber
from sqlalchemy.orm import Session

from .. import models

def parse_date_string(date_str: str) -> Optional[date]:
    """Parse various date string formats and return a date object"""
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = date_str.strip()
    if not date_str:
        return None
    
    # Try different date formats
    date_formats = [
        '%Y-%m-%d',           # 2024-01-15
        '%Y/%m/%d',           # 2024/01/15
        '%d/%m/%Y',           # 15/01/2024
        '%m/%d/%Y',           # 01/15/2024
        '%d-%m-%Y',           # 15-01-2024
        '%Y-%m-%d %H:%M:%S',  # 2024-01-15 10:30:00
        '%Y-%m-%dT%H:%M:%S',  # 2024-01-15T10:30:00
        '%Y-%m-%dT%H:%M:%SZ', # 2024-01-15T10:30:00Z
        '%d/%m/%y',           # 15/01/24
        '%m/%d/%y',           # 01/15/24
        '%d-%m-%y',           # 15-01-24
        '%Y%m%d',             # 20240115
        '%d.%m.%Y',           # 15.01.2024
        '%d.%m.%y',           # 15.01.24
    ]
    
    for fmt in date_formats:
        try:
            parsed_datetime = datetime.strptime(date_str, fmt)
            return parsed_datetime.date()
        except ValueError:
            continue
    
    return None

def parse_csv(content: bytes, filename: str) -> List[Dict[str, Any]]:
    """Parse CSV content and normalize to standard record format"""
    try:
        # Decode content
        csv_text = content.decode('utf-8')
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_text))
        records = []
        
        for row_num, row in enumerate(reader, 1):
            # Skip empty rows
            if not any(row.values()):
                continue
                
            record = normalize_csv_record(row, filename, row_num)
            if record:
                records.append(record)
        
        return records
        
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {str(e)}")

def parse_pdf(content: bytes, filename: str) -> List[Dict[str, Any]]:
    """Parse PDF content using pdfplumber (text-based PDFs only)"""
    try:
        records = []
        
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    continue
                
                # Simple pattern matching for common emission data patterns
                # This is a basic implementation - production would need more sophisticated parsing
                lines = text.split('\n')
                
                for line_num, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Look for patterns like "2025-06-01 OceanLift tanker_voyage 3 9600 40000 HFO"
                    parts = line.split()
                    if len(parts) >= 6:
                        try:
                            record = normalize_pdf_record(parts, filename, page_num, line_num)
                            if record:
                                records.append(record)
                        except:
                            continue  # Skip lines that don't match expected pattern
        
        return records
        
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {str(e)}")

def normalize_csv_record(row: Dict[str, str], filename: str, row_num: int) -> Optional[Dict[str, Any]]:
    """Normalize CSV row to standard record format"""
    try:
        # Parse datetime
        occurred_at_str = row.get('occurred_at', '').strip()
        if not occurred_at_str:
            return None
            
        # Parse the date string to a date object
        occurred_at = parse_date_string(occurred_at_str)
        if not occurred_at:
            return None  # No valid date format found
        
        # Extract required fields
        supplier = row.get('supplier', '').strip()
        activity = row.get('activity', '').strip()
        scope = int(row.get('scope', 3))
        
        if not all([supplier, activity]):
            return None
        
        # Build inputs dict from available columns
        inputs = {}
        
        # Numeric inputs
        for field in ['distance_km', 'tonnage', 'kwh']:
            value = row.get(field, '').strip()
            if value:
                try:
                    inputs[field] = float(value)
                except ValueError:
                    pass
        
        # String inputs
        for field in ['fuel_type', 'region', 'origin', 'destination', 'route']:
            value = row.get(field, '').strip()
            if value:
                inputs[field] = value
        
        return {
            'occurred_at': occurred_at,
            'supplier': supplier,
            'activity': activity,
            'scope': scope,
            'inputs': inputs,
            'raw_text': str(row),
            'page': 1,
            'field': 'csv_row'
        }
        
    except Exception:
        return None

def normalize_pdf_record(parts: List[str], filename: str, page_num: int, line_num: int) -> Optional[Dict[str, Any]]:
    """Normalize PDF text parts to standard record format"""
    try:
        # Basic pattern: date supplier activity scope [numeric fields...] [string fields...]
        if len(parts) < 4:
            return None
        
        occurred_at = parse_date_string(parts[0])
        if not occurred_at:
            return None
        supplier = parts[1]
        activity = parts[2]
        scope = int(parts[3])
        
        inputs = {}
        
        # Try to extract numeric values (distance, tonnage, etc.)
        remaining_parts = parts[4:]
        
        # Look for common patterns
        if len(remaining_parts) >= 3:
            # Pattern: distance tonnage fuel_type
            try:
                inputs['distance_km'] = float(remaining_parts[0])
                inputs['tonnage'] = float(remaining_parts[1])
                inputs['fuel_type'] = remaining_parts[2]
            except ValueError:
                pass
        
        # Look for kWh values
        for part in remaining_parts:
            if part.isdigit() and len(part) >= 4:  # Likely kWh value
                inputs['kwh'] = float(part)
                break
        
        return {
            'occurred_at': occurred_at,
            'supplier': supplier,
            'activity': activity,
            'scope': scope,
            'inputs': inputs,
            'raw_text': ' '.join(parts),
            'page': page_num,
            'field': f'line_{line_num}'
        }
        
    except Exception:
        return None

def get_or_create_supplier(db: Session, supplier_name: str) -> Optional[models.Supplier]:
    """Get existing supplier or create new one"""
    if not supplier_name:
        return None
    
    # Try to find existing supplier
    supplier = db.query(models.Supplier).filter(
        models.Supplier.name.ilike(supplier_name.strip())
    ).first()
    
    if not supplier:
        # Create new supplier
        supplier = models.Supplier(
            name=supplier_name.strip(),
            sector='Unknown',
            region='Unknown',
            data_quality_score=50
        )
        db.add(supplier)
        db.commit()
        db.refresh(supplier)
    
    return supplier

def create_fingerprint(record: Dict[str, Any], factor: models.EmissionFactor, result: Dict[str, Any]) -> Dict[str, Any]:
    """Create normalized fingerprint for event traceability"""
    fingerprint = {
        'activity': record['activity'],
        'scope': record['scope'],
        'inputs': record['inputs'],
        'factor_ref': {
            'source': factor.source,
            'version': factor.version,
            'category': factor.activity_category
        },
        'method': result['method']
    }
    
    # Add route information if available
    inputs = record.get('inputs', {})
    if 'origin' in inputs and 'destination' in inputs:
        fingerprint['route'] = f"{inputs['origin']}-{inputs['destination']}"
    
    return fingerprint

def validate_record_quality(record: Dict[str, Any]) -> Dict[str, Any]:
    """Assess data quality and completeness of a record"""
    quality_score = 100
    flags = []
    missing_fields = []
    
    # Check for required fields
    if not record.get('occurred_at'):
        flags.append('missing_date')
        missing_fields.append('occurred_at')
        quality_score -= 30
    
    if not record.get('supplier'):
        flags.append('missing_supplier')
        missing_fields.append('supplier')
        quality_score -= 20
    
    if not record.get('activity'):
        flags.append('missing_activity')
        missing_fields.append('activity')
        quality_score -= 25
    
    # Check input completeness based on activity
    inputs = record.get('inputs', {})
    activity = record.get('activity', '').lower()
    
    if 'shipping' in activity or 'tanker' in activity:
        if not inputs.get('distance_km'):
            flags.append('missing_distance')
            quality_score -= 15
        if not inputs.get('tonnage'):
            flags.append('missing_tonnage')
            quality_score -= 10
        if not inputs.get('fuel_type'):
            flags.append('missing_fuel_type')
            quality_score -= 10
    
    elif 'electricity' in activity:
        if not inputs.get('kwh'):
            flags.append('missing_kwh')
            quality_score -= 20
    
    return {
        'quality_score': max(0, quality_score),
        'quality_flags': flags,
        'missing_fields': missing_fields,
        'completeness_pct': max(0, quality_score)
    }

def extract_metadata(record: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from record for analysis"""
    metadata = {
        'has_location': bool(record.get('inputs', {}).get('region')),
        'has_route': bool(record.get('inputs', {}).get('origin') and record.get('inputs', {}).get('destination')),
        'input_count': len(record.get('inputs', {})),
        'numeric_inputs': len([v for v in record.get('inputs', {}).values() if isinstance(v, (int, float))]),
        'text_inputs': len([v for v in record.get('inputs', {}).values() if isinstance(v, str)])
    }
    
    return metadata
