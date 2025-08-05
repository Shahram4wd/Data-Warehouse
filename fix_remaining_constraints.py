#!/usr/bin/env python
"""
Simple script to check which field is causing the VARCHAR(50) error
"""
import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

def check_actual_constraints():
    """Check what the actual database constraints are"""
    with connection.cursor() as cursor:
        # Check all character fields and their current constraints
        cursor.execute("""
            SELECT column_name, character_maximum_length, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'ingestion_leadconduit_lead' 
            AND data_type = 'character varying'
            ORDER BY character_maximum_length ASC, column_name;
        """)
        
        all_constraints = cursor.fetchall()
        print("Current database field constraints:")
        print("=" * 50)
        for row in all_constraints:
            print(f"{row[0]:<30}: {row[2]}({row[1]})")
        
        # Find any fields still limited to 50 characters
        fields_50_or_less = [row[0] for row in all_constraints if row[1] and row[1] <= 50]
        
        if fields_50_or_less:
            print(f"\nFields with 50 chars or less:")
            for field in fields_50_or_less:
                print(f"  {field}")
            
            # Let's increase all fields with 50 chars or less to 255 chars
            print(f"\nUpdating all small fields to VARCHAR(255)...")
            for field in fields_50_or_less:
                print(f"Updating {field}...")
                cursor.execute(f"""
                    ALTER TABLE ingestion_leadconduit_lead 
                    ALTER COLUMN {field} TYPE VARCHAR(255);
                """)
        
        # Verify final state
        cursor.execute("""
            SELECT column_name, character_maximum_length, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'ingestion_leadconduit_lead' 
            AND data_type = 'character varying'
            ORDER BY character_maximum_length ASC, column_name;
        """)
        
        final_constraints = cursor.fetchall()
        print(f"\nFinal database field constraints:")
        print("=" * 50)
        for row in final_constraints:
            print(f"{row[0]:<30}: {row[2]}({row[1]})")

if __name__ == "__main__":
    check_actual_constraints()
