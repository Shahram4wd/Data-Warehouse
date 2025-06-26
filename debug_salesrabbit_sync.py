#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from ingestion.salesrabbit.salesrabbit_client import SalesRabbitClient
from ingestion.models.salesrabbit import SalesRabbit_Lead
from django.conf import settings
from django.utils.dateparse import parse_datetime
from datetime import datetime
import json

def debug_sync():
    print("=== SalesRabbit Sync Debug ===")
    
    # Test API connection
    print("1. Testing API connection...")
    client = SalesRabbitClient(api_token=settings.SALESRABBIT_API_TOKEN)
    response = client.get_leads()
    
    leads = response.get('data', []) if isinstance(response, dict) else response
    print(f"API returned {len(leads)} leads")
    
    if not leads:
        print("No leads returned from API!")
        return
    
    # Show first lead structure
    print("\n2. First lead structure:")
    first_lead = leads[0]
    print(json.dumps(first_lead, indent=2)[:500] + "...")
    
    # Test database insert with first lead
    print("\n3. Testing database insert with first lead...")
    lead_data = first_lead
    
    try:
        print(f"Lead ID: {lead_data.get('id')} (type: {type(lead_data.get('id'))})")
        
        # Check if lead already exists
        existing_count = SalesRabbit_Lead.objects.filter(id=lead_data['id']).count()
        print(f"Existing leads with this ID: {existing_count}")
        
        # Test the data mapping
        defaults = {
            'business_name': lead_data.get('businessName'),
            'first_name': lead_data.get('firstName'),
            'last_name': lead_data.get('lastName'),
            'email': lead_data.get('email'),
            'phone_primary': lead_data.get('phonePrimary'),
            'phone_alternate': lead_data.get('phoneAlternate'),
            'street1': lead_data.get('street1'),
            'street2': lead_data.get('street2'),
            'city': lead_data.get('city'),
            'state': lead_data.get('state'),
            'zip': lead_data.get('zip'),
            'country': lead_data.get('country'),
            'latitude': lead_data.get('latitude'),
            'longitude': lead_data.get('longitude'),
            'status': lead_data.get('status'),
            'campaign_id': lead_data.get('campaignId'),
            'user_id': lead_data.get('userId'),
            'user_name': lead_data.get('userName'),
            'notes': lead_data.get('notes'),
            'custom_fields': lead_data.get('customFields'),
            'date_created': parse_datetime(lead_data.get('dateCreated')) if lead_data.get('dateCreated') else None,
            'date_modified': parse_datetime(lead_data.get('dateModified')) if lead_data.get('dateModified') else None,
            'deleted_at': parse_datetime(lead_data.get('deletedAt')) if lead_data.get('deletedAt') else None,
            'status_modified': parse_datetime(lead_data.get('statusModified')) if lead_data.get('statusModified') else None,
            'owner_modified': parse_datetime(lead_data.get('ownerModified')) if lead_data.get('ownerModified') else None,
            'date_of_birth': parse_datetime(lead_data.get('dateOfBirth')) if lead_data.get('dateOfBirth') else None,
            'synced_at': datetime.now(),
            'data': lead_data,
        }
        
        print("Mapped data:")
        for key, value in defaults.items():
            if value is not None:
                print(f"  {key}: {value} (type: {type(value)})")
        
        # Try to create the lead
        print("\n4. Attempting to create lead...")
        lead_obj, created = SalesRabbit_Lead.objects.update_or_create(
            id=lead_data['id'],
            defaults=defaults
        )
        
        print(f"Lead {'created' if created else 'updated'}: {lead_obj}")
        print(f"Total leads in database: {SalesRabbit_Lead.objects.count()}")
        
    except Exception as e:
        print(f"Error creating lead: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_sync()
