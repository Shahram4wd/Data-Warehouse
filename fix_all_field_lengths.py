#!/usr/bin/env python
"""
Script to fix all field length constraints in LeadConduit models
"""
import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

def fix_all_field_lengths():
    """Increase all potentially problematic field lengths"""
    with connection.cursor() as cursor:
        # Check current constraints for all character fields
        cursor.execute("""
            SELECT column_name, character_maximum_length, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'ingestion_leadconduit_lead' 
            AND data_type = 'character varying'
            ORDER BY character_maximum_length, column_name;
        """)
        
        current_constraints = cursor.fetchall()
        print("Current field constraints:")
        for row in current_constraints:
            print(f"  {row[0]}: {row[2]}({row[1]})")
        
        # Update all problematic fields to be more generous
        print("\nUpdating field lengths...")
        
        updates = [
            ("phone", 50),               # was 50, should be good
            ("zip_code", 50),           # was 30, increase to 50 for international codes
            ("address", 500),           # was 255, increase to 500 for long addresses
            ("first_name", 200),        # was 100, increase to 200
            ("last_name", 200),         # was 100, increase to 200
            ("city", 200),              # was 100, increase to 200
            ("state", 100),             # was 50, increase to 100
            ("country", 100),           # was 100, should be good
            ("email", 255),             # EmailField, should be good but check
        ]
        
        for field_name, new_length in updates:
            print(f"Updating {field_name} to VARCHAR({new_length})...")
            cursor.execute(f"""
                ALTER TABLE ingestion_leadconduit_lead 
                ALTER COLUMN {field_name} TYPE VARCHAR({new_length});
            """)
        
        # Also check lead_id field which might be an issue
        print("Updating lead_id to VARCHAR(100)...")
        cursor.execute("""
            ALTER TABLE ingestion_leadconduit_lead 
            ALTER COLUMN lead_id TYPE VARCHAR(100);
        """)
        
        # Verify changes
        cursor.execute("""
            SELECT column_name, character_maximum_length, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'ingestion_leadconduit_lead' 
            AND data_type = 'character varying'
            ORDER BY character_maximum_length DESC, column_name;
        """)
        
        updated_constraints = cursor.fetchall()
        print("\nUpdated field constraints:")
        for row in updated_constraints:
            print(f"  {row[0]}: {row[2]}({row[1]})")
        
        print("\nField length fix completed successfully!")

if __name__ == "__main__":
    fix_all_field_lengths()
