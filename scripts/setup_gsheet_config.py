#!/usr/bin/env python3
"""
Google Sheets Configuration Setup Script

This script helps set up the initial configuration for Google Sheets sync.
Run this after setting up OAuth2 credentials.
"""

import os
import sys
import django
from datetime import datetime

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_dir)

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from ingestion.models.gsheet import GoogleSheetConfig
from ingestion.sync.gsheet.clients.marketing_leads import MarketingLeadsClient


def setup_marketing_leads_config():
    """Set up configuration for Marketing Leads sheet"""
    
    print("Setting up Marketing Leads Google Sheet configuration...")
    
    # Check if config already exists
    config, created = GoogleSheetConfig.objects.get_or_create(
        sheet_name='marketing_leads',
        defaults={
            'sheet_id': '1FRKfuMSrm9DrdIe_vtZJn7usUpuXPDWl4TB1k7Ae4xo',
            'tab_name': 'Marketing Source Leads',
            'is_active': True,
            'header_row': 1,
            'data_start_row': 2,
            'column_mapping': {
                'Date': 'date',
                'Source': 'source',
                'Medium': 'medium',
                'Campaign': 'campaign',
                'Leads': 'leads',
                'Cost': 'cost'
            },
            'ignored_columns': [],
            'target_model': 'GoogleSheetMarketingLead'
        }
    )
    
    if created:
        print("✓ Created new Marketing Leads configuration")
    else:
        print("✓ Marketing Leads configuration already exists")
    
    # Test connection and get sheet info
    try:
        client = MarketingLeadsClient()
        
        print("\nTesting Google Sheets connection...")
        if client.test_connection():
            print("✓ Google Sheets API connection successful")
            
            # Get sheet info
            sheet_info = client.get_sheet_info()
            print(f"\nSheet Information:")
            print(f"  Name: {sheet_info.get('name', 'Unknown')}")
            print(f"  Headers: {sheet_info.get('headers', [])}")
            print(f"  Header count: {sheet_info.get('header_count', 0)}")
            print(f"  Estimated data rows: {sheet_info.get('estimated_data_rows', 0)}")
            print(f"  Last modified: {sheet_info.get('last_modified', 'Unknown')}")
            
            # Update config with actual headers
            actual_headers = sheet_info.get('headers', [])
            if actual_headers:
                # Auto-generate column mapping
                auto_mapping = {}
                for header in actual_headers:
                    header_lower = header.lower()
                    if 'date' in header_lower:
                        auto_mapping[header] = 'date'
                    elif 'source' in header_lower:
                        auto_mapping[header] = 'source'
                    elif 'medium' in header_lower:
                        auto_mapping[header] = 'medium'
                    elif 'campaign' in header_lower:
                        auto_mapping[header] = 'campaign'
                    elif 'lead' in header_lower:
                        auto_mapping[header] = 'leads'
                    elif 'cost' in header_lower or 'spend' in header_lower:
                        auto_mapping[header] = 'cost'
                
                if auto_mapping:
                    config.column_mapping = auto_mapping
                    config.save()
                    print(f"\n✓ Updated column mapping: {auto_mapping}")
        
        else:
            print("✗ Google Sheets API connection failed")
            print("Please check your credentials and authentication setup")
            
    except Exception as e:
        print(f"✗ Error testing connection: {e}")
        print("Please check your Google Sheets setup and credentials")


def main():
    """Main setup function"""
    
    print("Google Sheets Configuration Setup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("Error: This script must be run from the Django project root directory")
        sys.exit(1)
    
    # Check if credentials file exists
    if not os.path.exists('credentials.json'):
        print("Warning: credentials.json not found in project root")
        print("Please follow the authentication setup guide first")
        print()
    
    try:
        # Set up marketing leads configuration
        setup_marketing_leads_config()
        
        print("\n" + "=" * 40)
        print("Setup completed successfully!")
        print("\nNext steps:")
        print("1. Test the sync: python manage.py sync_gsheet_marketing_leads --test-connection")
        print("2. Run a dry run: python manage.py sync_gsheet_marketing_leads --dry-run")
        print("3. Perform actual sync: python manage.py sync_gsheet_marketing_leads")
        
    except Exception as e:
        print(f"Error during setup: {e}")
        print("\nPlease check:")
        print("1. Django database is set up (python manage.py migrate)")
        print("2. Google credentials are configured")
        print("3. You have access to the Google Sheet")


if __name__ == '__main__':
    main()
