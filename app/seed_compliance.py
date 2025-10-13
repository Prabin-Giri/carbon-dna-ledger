#!/usr/bin/env python3
"""
Compliance Rules Seeder

This script seeds the database with comprehensive compliance rules
for all major business compliance frameworks.
"""
import json
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

from .db import get_db
from .models import ComplianceRule
from sqlalchemy.orm import Session

def load_compliance_data():
    """Load compliance data from JSON file"""
    json_path = Path(__file__).parent.parent / "infra" / "seed_compliance_rules.json"
    
    if not json_path.exists():
        print(f"❌ Compliance data file not found: {json_path}")
        return None
    
    with open(json_path, 'r') as f:
        return json.load(f)

def seed_compliance_rules(db: Session, compliance_data: dict):
    """Seed compliance rules into the database"""
    rules_data = compliance_data.get('compliance_rules', [])
    
    print(f"📊 Seeding {len(rules_data)} compliance rules...")
    
    seeded_count = 0
    skipped_count = 0
    
    for rule_data in rules_data:
        try:
            # Check if rule already exists
            existing_rule = db.query(ComplianceRule).filter(
                ComplianceRule.rule_id == rule_data['rule_id']
            ).first()
            
            if existing_rule:
                print(f"   ⏭️  Skipping existing rule: {rule_data['rule_id']}")
                skipped_count += 1
                continue
            
            # Create new compliance rule
            compliance_rule = ComplianceRule(
                rule_id=rule_data['rule_id'],
                framework=rule_data['framework'],
                rule_name=rule_data['rule_name'],
                rule_description=rule_data['rule_description'],
                conditions=rule_data['conditions'],
                severity=rule_data['severity'],
                auto_apply=rule_data['auto_apply'],
                required_fields=rule_data.get('required_fields', []),
                validation_rules=rule_data.get('validation_rules', []),
                threshold_values=rule_data.get('threshold_values', {}),
                is_active=True
            )
            
            db.add(compliance_rule)
            seeded_count += 1
            print(f"   ✅ Seeded rule: {rule_data['rule_id']} - {rule_data['rule_name']}")
            
        except Exception as e:
            print(f"   ❌ Error seeding rule {rule_data.get('rule_id', 'Unknown')}: {e}")
            continue
    
    # Commit all changes
    try:
        db.commit()
        print(f"\n🎉 Successfully seeded {seeded_count} compliance rules!")
        print(f"📊 Skipped {skipped_count} existing rules")
        return True
    except Exception as e:
        print(f"❌ Error committing changes: {e}")
        db.rollback()
        return False

def main():
    """Main seeding function"""
    print("🌱 Starting Compliance Rules Seeding...")
    
    # Load compliance data
    compliance_data = load_compliance_data()
    if not compliance_data:
        return False
    
    # Get database session
    db = next(get_db())
    
    try:
        # Seed compliance rules
        success = seed_compliance_rules(db, compliance_data)
        
        if success:
            print("\n✅ Compliance rules seeding completed successfully!")
            
            # Show summary
            total_rules = db.query(ComplianceRule).count()
            print(f"📊 Total compliance rules in database: {total_rules}")
            
            # Show rules by framework
            frameworks = db.query(ComplianceRule.framework).distinct().all()
            print(f"📋 Frameworks covered: {len(frameworks)}")
            for framework in frameworks:
                framework_name = framework[0]
                rule_count = db.query(ComplianceRule).filter(
                    ComplianceRule.framework == framework_name
                ).count()
                print(f"   - {framework_name}: {rule_count} rules")
            
            return True
        else:
            print("❌ Compliance rules seeding failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
