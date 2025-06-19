#!/usr/bin/env python
"""
Test script to find working Arrivy API endpoints for team members
"""
import asyncio
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from ingestion.arrivy.arrivy_client import ArrivyClient

async def test_endpoints():
    """Test various potential endpoints for team members"""
    client = ArrivyClient()
    
    # List of potential endpoints to try
    endpoints = [
        'team',
        'users', 
        'employees',
        'staff',
        'workers',
        'members',
        'people',
        'resources',
        'personnel',
        'team_members',
        'teamMembers',
        'team-members'
    ]
    
    print("Testing potential team member endpoints...")
    
    for endpoint in endpoints:
        try:
            print(f"\n--- Testing endpoint: {endpoint} ---")
            result = await client._make_request(endpoint, params={'page_size': 1, 'page': 1})
            
            if result and result.get('data'):
                print(f"✅ SUCCESS: {endpoint} returned data!")
                print(f"Data preview: {str(result)[:200]}...")
                break
            else:
                print(f"❌ No data returned from {endpoint}")
                
        except Exception as e:
            error_msg = str(e)
            if "Authentication failed" in error_msg:
                print(f"🔐 Auth error for {endpoint}: {error_msg}")
            elif "Failed to parse JSON" in error_msg or "HTML" in error_msg:
                print(f"📄 HTML response for {endpoint} (likely invalid endpoint)")
            else:
                print(f"❌ Error for {endpoint}: {error_msg}")
    
    # Also try testing if we can get individual team members by ID
    # if we know any IDs from booking data
    print("\n--- Testing individual team member access ---")
    try:
        # Try some common ID patterns
        test_ids = ['1', '123', '1000']
        for test_id in test_ids:
            try:
                result = await client._make_request(f"team/{test_id}")
                if result:
                    print(f"✅ Team member ID {test_id} accessible!")
                    break
            except:
                continue
    except Exception as e:
        print(f"Individual access test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoints())
