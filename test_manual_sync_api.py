#!/usr/bin/env python
"""
Test the manual sync API endpoint
"""
import requests
import json

def test_manual_sync_api():
    """Test the manual sync API endpoint"""
    
    # Test data that simulates what JavaScript would send
    test_data = {
        'crm_source': 'genius',
        'sync_type': 'appointmentoutcomes',  # This comes from JavaScript modelNameToSyncType
        'parameters': {
            'force': False,
            'full': False,
            'dry_run': True,
            'debug': True
        }
    }
    
    url = 'http://localhost:8000/ingestion/crm-dashboard/api/sync/execute/'
    
    print(f"Testing manual sync API at: {url}")
    print(f"Payload: {json.dumps(test_data, indent=2)}")
    
    try:
        # First get CSRF token
        session = requests.Session()
        response = session.get('http://localhost:8000/ingestion/crm-dashboard/')
        
        if response.status_code == 200:
            # Extract CSRF token from cookies
            csrf_token = session.cookies.get('csrftoken')
            
            if csrf_token:
                headers = {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf_token,
                    'Referer': 'http://localhost:8000/ingestion/crm-dashboard/'
                }
                
                # Make the sync request
                sync_response = session.post(url, 
                                           json=test_data, 
                                           headers=headers)
                
                print(f"Response Status: {sync_response.status_code}")
                print(f"Response Body: {sync_response.text}")
                
                if sync_response.status_code == 200:
                    result = sync_response.json()
                    print(f"Sync Result: {json.dumps(result, indent=2)}")
                else:
                    print(f"API Error: {sync_response.status_code} - {sync_response.text}")
            else:
                print("Failed to get CSRF token")
        else:
            print(f"Failed to access dashboard: {response.status_code}")
            
    except Exception as e:
        print(f"Error testing manual sync: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_manual_sync_api()
