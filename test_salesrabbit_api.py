#!/usr/bin/env python
"""
Test script to check SalesRabbit Users API directly
"""
import asyncio
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from ingestion.sync.salesrabbit.clients.users import SalesRabbitUsersClient

async def test_api():
    print("Testing SalesRabbit Users API...")
    client = SalesRabbitUsersClient()
    
    try:
        async with client as c:
            # Test without pagination first
            print("Testing with limit=10...")
            response = await c.make_request('GET', '/users', params={'limit': 10})
            print(f'Response type: {type(response)}')
            
            if isinstance(response, list):
                print(f'Got {len(response)} users (list format)')
                if response:
                    print(f'First user ID: {response[0].get("id", "no id")}')
                    print(f'Sample user keys: {list(response[0].keys())[:5]}')
            elif isinstance(response, dict):
                print(f'Response keys: {list(response.keys())}')
                users = response.get('data', response.get('users', []))
                print(f'Got {len(users)} users from response data')
                if users:
                    print(f'First user ID: {users[0].get("id", "no id")}')
            else:
                print(f'Unexpected response: {response}')
                
            # Test with page parameter
            print("\nTesting with limit=10, page=1...")
            response2 = await c.make_request('GET', '/users', params={'limit': 10, 'page': 1})
            if isinstance(response2, dict):
                print(f'Page 1: Got {len(response2.get("data", []))} users')
                print(f'Page 1 meta: {response2.get("meta", {})}')
            else:
                print(f'Page 1: Response type {type(response2)}')
                
            # Test with page 0
            print("\nTesting with limit=10, page=0...")
            response3 = await c.make_request('GET', '/users', params={'limit': 10, 'page': 0})
            if isinstance(response3, dict):
                print(f'Page 0: Got {len(response3.get("data", []))} users')
                print(f'Page 0 meta: {response3.get("meta", {})}')
            else:
                print(f'Page 0: Response type {type(response3)}')
                
    except Exception as e:
        print(f"Error testing API: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())