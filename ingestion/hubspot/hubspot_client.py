import logging
import json
import sys
from datetime import datetime
import aiohttp
from django.conf import settings

logger = logging.getLogger(__name__)

class HubspotClient:
    """Asynchronous client for interacting with the Hubspot API."""
    
    BASE_URL = "https://api.hubapi.com"
    TIMEOUT = 30  # 30 second timeout for API requests
    
    def __init__(self, api_token=None):
        self.api_token = api_token or settings.HUBSPOT_API_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        print(f"Initialized HubspotClient with token: {self.api_token[:5]}...{self.api_token[-5:]} (length: {len(self.api_token)})")
    
    async def discover_endpoints(self, session):
        """Discover available endpoints in the Hubspot API."""
        url = f"{self.BASE_URL}/crm/v3/schemas"
        print(f"Discovering endpoints from: {url}")
        
        try:
            async with session.get(url, headers=self.headers, timeout=self.TIMEOUT) as response:
                status = response.status
                print(f"Endpoints discovery response status: {status}")
                
                if status != 200:
                    response_text = await response.text()
                    print(f"Failed to discover endpoints. Status: {status}, Response: {response_text}")
                    return []
                    
                data = await response.json()
                
            endpoints = [
                schema.get("objectTypeId")
                for schema in data.get("results", [])
                if schema.get("objectTypeId")
            ]
            print(f"Discovered endpoints: {endpoints}")
            return endpoints
        except aiohttp.ClientError as e:
            print(f"Network error discovering endpoints: {str(e)}")
            return []
        except Exception as e:
            print(f"Unexpected error discovering endpoints: {str(e)}")
            return []
    
    async def get_data(self, session, endpoint, params=None):
        """Get data from a specific Hubspot endpoint."""
        url = f"{self.BASE_URL}/crm/v3/objects/{endpoint}"
        params = params or {}
        print(f"Fetching data from endpoint: {url} with params: {params}")
        
        try:
            print(f"Sending request to {url}...")
            async with session.get(url, headers=self.headers, params=params, timeout=self.TIMEOUT) as response:
                status = response.status
                print(f"API response status: {status}")
                
                if status != 200:
                    response_text = await response.text()
                    print(f"Failed to fetch data for endpoint {endpoint}. Status: {status}, Response: {response_text}")
                    return None
                
                print(f"Parsing JSON response...")
                data = await response.json()
                result_count = len(data.get('results', []))
                print(f"Retrieved {result_count} records from {endpoint}")
                
                # Log sample data for debugging (first record only)
                if result_count > 0:
                    sample = data['results'][0]
                    print(f"Sample data: {json.dumps(sample)[:200]}...")
                    
                return data
        except aiohttp.ClientError as e:
            print(f"Network error in API request to {url}: {str(e)}")
            return None
        except asyncio.TimeoutError:
            print(f"Timeout error in API request to {url}")
            return None
        except Exception as e:
            print(f"Unexpected error in API request to {url}: {str(e)}")
            return None
    
    async def get_all_data(self, session, endpoint, last_sync=None):
        """Get all data from a specific Hubspot endpoint with pagination."""
        # Use a small limit for testing
        params = {"limit": 10, "properties": ["*"]}
        if last_sync:
            params["updatedAfter"] = last_sync.isoformat()
        
        print(f"Starting pagination for endpoint {endpoint}")
        all_results = []
        page_count = 0
        max_pages = 10  # Limit to 10 pages for safety during testing
        
        while page_count < max_pages:
            page_count += 1
            print(f"Fetching page {page_count} for endpoint {endpoint}")
            
            data = await self.get_data(session, endpoint, params)
            if not data:
                print(f"No data returned for page {page_count} - stopping pagination")
                break
                
            results = data.get("results", [])
            if not results:
                print(f"No results in page {page_count} - stopping pagination")
                break
                
            print(f"Retrieved {len(results)} records in page {page_count}")
            all_results.extend(results)
            
            # For testing purposes, only get first page
            if page_count == 1:
                print("Limiting to first page for testing")
                break
                
            paging = data.get("paging", {})
            next_page = paging.get("next", {}).get("after")
            if next_page:
                print(f"Next page token: {next_page}")
                params["after"] = next_page
            else:
                print("No more pages available")
                break
        
        print(f"Retrieved a total of {len(all_results)} records from {endpoint}")
        return all_results
