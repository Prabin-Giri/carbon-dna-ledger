"""
Seed script to initialize database with demo data
Run with: python -m app.seed
"""
import json
import os
import sys
from datetime import datetime

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import sessionmaker
from app.db import engine
from app import models
from app.services import ingest

def seed_suppliers(db):
    """Create demo suppliers"""
    suppliers = [
        {
            'name': 'OceanLift',
            'sector': 'Shipping',
            'region': 'Global',
            'data_quality_score': 75
        },
        {
            'name': 'GridCo',
            'sector': 'Energy',
            'region': 'NL',
            'data_quality_score': 85
        },
        {
            'name': 'RefineMax',
            'sector': 'Oil & Gas',
            'region': 'US',
            'data_quality_score': 60
        }
    ]
    
    for supplier_data in suppliers:
        # Check if supplier already exists
        existing = db.query(models.Supplier).filter(
            models.Supplier.name == supplier_data['name']
        ).first()
        
        if not existing:
            supplier = models.Supplier(**supplier_data)
            db.add(supplier)
    
    db.commit()
    print("✓ Suppliers seeded")

def seed_emission_factors(db):
    """Load emission factors from JSON file"""
    factors_file = os.path.join(os.path.dirname(__file__), '..', 'infra', 'seed_factors.json')
    
    with open(factors_file, 'r') as f:
        factors_data = json.load(f)
    
    for factor_data in factors_data:
        # Check if factor already exists
        existing = db.query(models.EmissionFactor).filter(
            models.EmissionFactor.source == factor_data['source'],
            models.EmissionFactor.activity_category == factor_data['activity_category'],
            models.EmissionFactor.version == factor_data['version']
        ).first()
        
        if not existing:
            factor = models.EmissionFactor(**factor_data)
            db.add(factor)
    
    db.commit()
    print("✓ Emission factors seeded")

def seed_demo_events(db):
    """Load and process demo CSV data"""
    csv_file = os.path.join(os.path.dirname(__file__), '..', 'infra', 'seed_demo.csv')
    
    # Read CSV content
    with open(csv_file, 'rb') as f:
        content = f.read()
    
    # Parse CSV using the same ingestion pipeline
    try:
        records = ingest.parse_csv(content, 'seed_demo.csv')
        print(f"Parsed {len(records)} records from demo CSV")
        
        # Process each record through the full ingestion pipeline
        from app.services import factors, hashing
        
        for record in records:
            # Get supplier
            supplier = ingest.get_or_create_supplier(db, record['supplier'])
            if not supplier:
                print(f"Warning: Could not create supplier for {record['supplier']}")
                continue
            
            # Match emission factor
            factor = factors.match_emission_factor(db, record)
            if not factor:
                print(f"Warning: No matching factor for activity {record['activity']}")
                continue
            
            # Calculate emissions
            result = factors.calculate_emissions(record, factor)
            
            # Get previous hash for chaining
            prev_hash = hashing.get_last_hash(db)
            
            # Create event data
            event_data = {
                'supplier_id': supplier.id,
                'occurred_at': record['occurred_at'],
                'activity': record['activity'],
                'scope': record['scope'],
                'inputs': record['inputs'],
                'factor_id': factor.id,
                'method': result['method'],
                'result_kgco2e': result['result_kgco2e'],
                'uncertainty_pct': result['uncertainty_pct'],
                'source_doc': [{
                    'doc_id': 'seed_demo.csv',
                    'page': 1,
                    'field': 'csv_row',
                    'raw_text': str(record)
                }],
                'quality_flags': result.get('quality_flags', []) if isinstance(result.get('quality_flags', []), list) else [],
                'fingerprint': ingest.create_fingerprint(record, factor, result),
                'prev_hash': prev_hash
            }
            
            # Calculate row hash
            row_hash = hashing.calculate_row_hash(event_data, prev_hash)
            event_data['row_hash'] = row_hash
            
            # Create and insert event
            event = models.CarbonEvent(**event_data)
            db.add(event)
            db.commit()
            db.refresh(event)
            
            print(f"✓ Created event {event.id} for {supplier.name}")
        
        print(f"✓ Demo events seeded")
        
    except Exception as e:
        print(f"Error seeding demo events: {str(e)}")
        db.rollback()

def main():
    """Main seeding function"""
    print("🌱 Seeding Carbon DNA Ledger database...")
    
    # Create database session
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Create tables if they don't exist
        models.Base.metadata.create_all(bind=engine)
        print("✓ Database tables created")
        
        # Seed data
        seed_suppliers(db)
        seed_emission_factors(db)
        seed_demo_events(db)
        
        print("🎉 Database seeding completed successfully!")
        
        # Print summary
        supplier_count = db.query(models.Supplier).count()
        factor_count = db.query(models.EmissionFactor).count()
        event_count = db.query(models.CarbonEvent).count()
        
        print(f"\nDatabase summary:")
        print(f"  - Suppliers: {supplier_count}")
        print(f"  - Emission Factors: {factor_count}")
        print(f"  - Carbon Events: {event_count}")
        
        # Test hash chain integrity
        if event_count > 0:
            from app.services import hashing
            first_event = db.query(models.CarbonEvent).order_by(models.CarbonEvent.created_at).first()
            last_event = db.query(models.CarbonEvent).order_by(models.CarbonEvent.created_at.desc()).first()
            
            print(f"\nHash chain info:")
            print(f"  - First event hash: {first_event.row_hash[:16]}...")
            print(f"  - Last event hash: {last_event.row_hash[:16]}...")
            print(f"  - Hash chain length: {event_count}")
        
    except Exception as e:
        print(f"❌ Error during seeding: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
