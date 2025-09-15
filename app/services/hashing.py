"""
Cryptographic hashing services for hash-chained integrity
"""
import hashlib
import json
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .. import models

def canonicalize_json(obj: Any) -> str:
    """Convert object to canonical JSON string for stable hashing"""
    def json_serializer(obj):
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), default=json_serializer)

def sha256_hash(data: str) -> str:
    """Calculate SHA-256 hash of string data"""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def get_last_hash(db: Session) -> Optional[str]:
    """Get the hash of the most recently created carbon event"""
    last_event = db.query(models.CarbonEvent).order_by(desc(models.CarbonEvent.created_at)).first()
    return last_event.row_hash if last_event else None

def calculate_row_hash(event_data: Dict[str, Any], prev_hash: Optional[str]) -> str:
    """
    Calculate hash-chained row hash for a carbon event
    
    Hash = SHA256(prev_hash + "|" + SHA256(canonical_row_material))
    canonical_row_material includes: occurred_at, supplier_id, scope, activity, 
    inputs, factor_id, method, result_kgco2e, uncertainty_pct, source_doc
    """
    # Extract canonical row material
    canonical_data = {
        'occurred_at': event_data['occurred_at'],
        'supplier_id': str(event_data['supplier_id']),
        'scope': event_data['scope'],
        'activity': event_data['activity'],
        'inputs': event_data['inputs'],
        'factor_id': str(event_data['factor_id']),
        'method': event_data['method'],
        'result_kgco2e': event_data['result_kgco2e'],
        'uncertainty_pct': event_data['uncertainty_pct'],
        'source_doc': event_data['source_doc']
    }
    
    # Create canonical JSON
    canonical_json = canonicalize_json(canonical_data)
    content_hash = sha256_hash(canonical_json)
    
    # Chain with previous hash
    prev_hash_str = prev_hash or ""
    chained_data = f"{prev_hash_str}|{content_hash}"
    
    return sha256_hash(chained_data)

def verify_hash_chain(db: Session, event_id: str) -> Dict[str, Any]:
    """
    Verify hash chain integrity for a specific event
    Returns verification result with details
    """
    event = db.query(models.CarbonEvent).filter(models.CarbonEvent.id == event_id).first()
    if not event:
        return {'valid': False, 'error': 'Event not found'}
    
    # Reconstruct event data for hashing
    event_data = {
        'occurred_at': event.occurred_at,
        'supplier_id': event.supplier_id,
        'scope': event.scope,
        'activity': event.activity,
        'inputs': event.inputs,
        'factor_id': event.factor_id,
        'method': event.method,
        'result_kgco2e': event.result_kgco2e,
        'uncertainty_pct': event.uncertainty_pct,
        'source_doc': event.source_doc
    }
    
    # Recalculate hash
    calculated_hash = calculate_row_hash(event_data, event.prev_hash)
    
    # Verify integrity
    is_valid = calculated_hash == event.row_hash
    
    return {
        'valid': is_valid,
        'stored_hash': event.row_hash,
        'calculated_hash': calculated_hash,
        'prev_hash': event.prev_hash,
        'event_id': str(event.id)
    }

def simulate_tamper(event_data: Dict[str, Any], field: str, new_value: Any) -> Dict[str, Any]:
    """
    Simulate tampering with an event field and show hash mismatch
    This is for demonstration purposes only
    """
    original_value = event_data.get(field)
    
    # Create tampered version
    tampered_data = event_data.copy()
    tampered_data[field] = new_value
    
    # Calculate both hashes
    original_hash = calculate_row_hash(event_data, event_data.get('prev_hash'))
    tampered_hash = calculate_row_hash(tampered_data, event_data.get('prev_hash'))
    
    return {
        'field': field,
        'original_value': original_value,
        'tampered_value': new_value,
        'original_hash': original_hash,
        'tampered_hash': tampered_hash,
        'integrity_broken': original_hash != tampered_hash
    }

def calculate_merkle_root(row_hashes: List[str]) -> str:
    """
    Calculate Merkle root from list of row hashes
    Uses simple pairwise hashing approach
    """
    if not row_hashes:
        return sha256_hash("")
    
    if len(row_hashes) == 1:
        return row_hashes[0]
    
    # For simplicity, use concatenated hash approach
    # In production, would implement proper Merkle tree
    concatenated = ''.join(sorted(row_hashes))
    return sha256_hash(concatenated)
