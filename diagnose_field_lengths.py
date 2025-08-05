#!/usr/bin/env python
"""
Script to diagnose which fields are too long in LeadConduit data
"""
import os
import sys
import django
import asyncio
from asgiref.sync import sync_to_async

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from ingestion.sync.leadconduit.clients.events import LeadConduitEventsClient
from ingestion.config.leadconduit_config import LeadConduitSyncConfig

async def diagnose_field_lengths():
    """Check actual field lengths in LeadConduit data"""
    config = LeadConduitSyncConfig()
    client = LeadConduitEventsClient(config)
    
    # Get a sample of events
    print("Fetching sample events...")
    events = await client.get_events_by_date_range('2025-08-05T00:00:00Z', '2025-08-05T01:00:00Z', limit=100)
    
    field_max_lengths = {}
    long_values = {}
    
    for event in events:
        lead_data = event.get('leadId', {})
        if isinstance(lead_data, dict):
            for field, value in lead_data.items():
                if isinstance(value, str):
                    field_length = len(value)
                    
                    # Track max length per field
                    if field not in field_max_lengths or field_length > field_max_lengths[field]:
                        field_max_lengths[field] = field_length
                    
                    # Track values that are too long for common limits
                    if field_length > 50:
                        if field not in long_values:
                            long_values[field] = []
                        long_values[field].append((value, field_length))
    
    print("\nField length analysis:")
    print("=" * 60)
    for field, max_length in sorted(field_max_lengths.items(), key=lambda x: x[1], reverse=True):
        print(f"{field:<30}: max={max_length}")
    
    print("\nValues exceeding 50 characters:")
    print("=" * 60)
    for field, values in long_values.items():
        print(f"\n{field}:")
        for value, length in values[:3]:  # Show first 3 examples
            print(f"  Length {length}: {value[:100]}...")
    
    # Check specific problematic lead IDs
    print("\nChecking specific problematic lead data:")
    print("=" * 60)
    problematic_ids = ['68914982ee0c38be2e2f7334', '68914499c0b4dbc1a567c63df']
    
    for event in events:
        lead_data = event.get('leadId', {})
        if isinstance(lead_data, dict):
            lead_id = lead_data.get('id')
            if lead_id in problematic_ids:
                print(f"\nLead ID: {lead_id}")
                for field, value in lead_data.items():
                    if isinstance(value, str) and len(value) > 50:
                        print(f"  {field} ({len(value)}): {value}")

if __name__ == "__main__":
    asyncio.run(diagnose_field_lengths())
