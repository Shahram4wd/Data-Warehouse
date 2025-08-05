#!/usr/bin/env python3
"""
Add missing fields to LeadConduit tables
"""
import os
import sys
import django
from django.db import connection, transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

def add_missing_fields():
    """Add missing fields to LeadConduit tables"""
    with connection.cursor() as cursor:
        # Check existing columns first
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'ingestion_leadconduit_lead' 
            ORDER BY ordinal_position
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        print(f"Existing columns: {existing_columns}")
        
        # Add missing fields to LeadConduit_Lead table
        missing_fields = []
        
        # Check for event_id
        if 'event_id' not in existing_columns:
            missing_fields.append("ADD COLUMN event_id VARCHAR(100)")
            
        # Check for other key fields
        if 'country' not in existing_columns:
            missing_fields.append("ADD COLUMN country VARCHAR(100)")
            
        if 'flow_name' not in existing_columns:
            missing_fields.append("ADD COLUMN flow_name VARCHAR(100)")
            
        if 'source_name' not in existing_columns:
            missing_fields.append("ADD COLUMN source_name VARCHAR(100)")
            
        if 'outcome' not in existing_columns:
            missing_fields.append("ADD COLUMN outcome VARCHAR(100)")
            
        if 'reason' not in existing_columns:
            missing_fields.append("ADD COLUMN reason VARCHAR(255)")
            
        if 'lead_data' not in existing_columns:
            missing_fields.append("ADD COLUMN lead_data JSONB DEFAULT '{}'")
            
        if 'submitted_utc' not in existing_columns:
            missing_fields.append("ADD COLUMN submitted_utc TIMESTAMP WITH TIME ZONE")
            
        if missing_fields:
            print(f"Adding {len(missing_fields)} missing fields...")
            
            with transaction.atomic():
                for field in missing_fields:
                    sql = f"ALTER TABLE ingestion_leadconduit_lead {field}"
                    print(f"Executing: {sql}")
                    cursor.execute(sql)
                    
                # Add indexes for key fields
                index_queries = [
                    "CREATE INDEX IF NOT EXISTS leadconduit_lead_event_id_idx ON ingestion_leadconduit_lead(event_id)",
                    "CREATE INDEX IF NOT EXISTS leadconduit_lead_flow_name_idx ON ingestion_leadconduit_lead(flow_name)",
                    "CREATE INDEX IF NOT EXISTS leadconduit_lead_source_name_idx ON ingestion_leadconduit_lead(source_name)",
                    "CREATE INDEX IF NOT EXISTS leadconduit_lead_outcome_idx ON ingestion_leadconduit_lead(outcome)",
                ]
                
                for index_query in index_queries:
                    print(f"Executing: {index_query}")
                    cursor.execute(index_query)
                    
            print("Successfully added missing fields and indexes!")
        else:
            print("All required fields already exist.")

if __name__ == "__main__":
    add_missing_fields()
