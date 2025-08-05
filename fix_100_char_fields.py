#!/usr/bin/env python
"""
Script to fix the remaining VARCHAR(100) field constraints
"""
import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

def fix_remaining_100_char_fields():
    """Increase remaining 100-character fields"""
    with connection.cursor() as cursor:
        # Check current 100-char fields
        cursor.execute("""
            SELECT column_name, character_maximum_length, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'ingestion_leadconduit_lead' 
            AND character_maximum_length = 100
            ORDER BY column_name;
        """)
        
        fields_100 = cursor.fetchall()
        print("Fields with 100 character limit:")
        for row in fields_100:
            print(f"  {row[0]}: {row[2]}({row[1]})")
        
        # Update all 100-char fields to 255
        if fields_100:
            print(f"\nUpdating all 100-char fields to VARCHAR(255)...")
            for row in fields_100:
                field_name = row[0]
                print(f"Updating {field_name}...")
                cursor.execute(f"""
                    ALTER TABLE ingestion_leadconduit_lead 
                    ALTER COLUMN {field_name} TYPE VARCHAR(255);
                """)
        
        # Check final state
        cursor.execute("""
            SELECT column_name, character_maximum_length, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'ingestion_leadconduit_lead' 
            AND data_type = 'character varying'
            ORDER BY character_maximum_length ASC, column_name;
        """)
        
        final_fields = cursor.fetchall()
        print(f"\nFinal field constraints:")
        print("=" * 50)
        for row in final_fields:
            print(f"{row[0]:<30}: {row[2]}({row[1]})")

if __name__ == "__main__":
    fix_remaining_100_char_fields()
