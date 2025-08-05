#!/usr/bin/env python
"""
Script to fix phone field length constraints in LeadConduit models
"""
import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

def fix_phone_field_length():
    """Increase phone field length from 20 to 50 characters"""
    with connection.cursor() as cursor:
        # Check current constraint
        cursor.execute("""
            SELECT column_name, character_maximum_length, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'ingestion_leadconduit_lead' 
            AND column_name IN ('phone', 'zip_code')
            ORDER BY column_name;
        """)
        
        current_constraints = cursor.fetchall()
        print("Current field constraints:")
        for row in current_constraints:
            print(f"  {row[0]}: {row[2]}({row[1]})")
        
        # Update phone field to allow longer values
        print("\nUpdating phone field length from 20 to 50...")
        cursor.execute("""
            ALTER TABLE ingestion_leadconduit_lead 
            ALTER COLUMN phone TYPE VARCHAR(50);
        """)
        
        # Also update zip_code which might have long international codes
        print("Updating zip_code field length from 20 to 30...")
        cursor.execute("""
            ALTER TABLE ingestion_leadconduit_lead 
            ALTER COLUMN zip_code TYPE VARCHAR(30);
        """)
        
        # Verify changes
        cursor.execute("""
            SELECT column_name, character_maximum_length, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'ingestion_leadconduit_lead' 
            AND column_name IN ('phone', 'zip_code')
            ORDER BY column_name;
        """)
        
        updated_constraints = cursor.fetchall()
        print("\nUpdated field constraints:")
        for row in updated_constraints:
            print(f"  {row[0]}: {row[2]}({row[1]})")
        
        print("\nPhone field length fix completed successfully!")

if __name__ == "__main__":
    fix_phone_field_length()
