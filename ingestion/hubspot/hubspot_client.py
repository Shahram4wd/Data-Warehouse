import aiohttp
import asyncio
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class HubspotClient:
    """Asynchronous client for interacting with the Hubspot API."""
    
    BASE_URL = "https://api.hubapi.com"
    
    def __init__(self, api_token=None):
        self.api_token = api_token or settings.HUBSPOT_API_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    async def discover_endpoints(self, session):
        """Discover available endpoints in the Hubspot API."""
        url = f"{self.BASE_URL}/crm/v3/schemas"
        async with session.get(url, headers=self.headers) as response:
            if response.status != 200:
                logger.error(f"Failed to discover endpoints. Status: {response.status}")
                return []
            data = await response.json()
            
        endpoints = [
            schema.get("objectTypeId")
            for schema in data.get("results", [])
            if schema.get("objectTypeId")
        ]
        return endpoints
    
    async def get_data(self, session, endpoint, params=None):
        """Get data from a specific Hubspot endpoint."""
        url = f"{self.BASE_URL}/crm/v3/objects/{endpoint}"
        params = params or {}
        
        async with session.get(url, headers=self.headers, params=params) as response:
            if response.status != 200:
                logger.error(f"Failed to fetch data for endpoint {endpoint}. Status: {response.status}")
                return None
            return await response.json()
    
    async def get_all_data(self, session, endpoint, last_sync=None):
        """Get all data from a specific Hubspot endpoint with pagination."""
        params = {}
        if last_sync:
            params["updatedAfter"] = last_sync.isoformat()
            
        all_results = []
        while True:
            data = await self.get_data(session, endpoint, params)
            if not data:
                break
                
            results = data.get("results", [])
            if not results:
                break
                
            all_results.extend(results)
            
            paging = data.get("paging", {})
            next_page = paging.get("next", {}).get("after")
            if next_page:
                params["after"] = next_page
            else:
                break
                
        return all_results
