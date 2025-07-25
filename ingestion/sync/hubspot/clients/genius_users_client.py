"""
Client for fetching Genius Users from HubSpot (custom object 2-42119425)
Follows import_refactoring.md enterprise architecture standards
"""
import aiohttp
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, AsyncGenerator, Tuple
from .base import HubSpotBaseClient

logger = logging.getLogger(__name__)

class HubSpotGeniusUsersClient(HubSpotBaseClient):
    def __init__(self, api_token=None):
        super().__init__(api_token=api_token)
        self.object_type = "2-42119425"

    async def fetch_users_batch(self, limit=100, after=None, properties=None):
        await self.authenticate()
        url = f"{self.base_url}/crm/v3/objects/{self.object_type}/"
        params = {"limit": limit}
        if after:
            params["after"] = after
        if properties:
            # HubSpot API expects comma-separated list for properties
            params["properties"] = ",".join(properties)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raw = await response.text()
                    raise Exception(f"HubSpot API error {response.status}: {raw}")

    async def fetch_genius_users(self, last_sync: Optional[datetime] = None, 
                                limit: int = 100, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch genius users from HubSpot API with pagination and delta sync support"""
        
        page_token = None
        
        while True:
            try:
                users, next_token = await self._fetch_users_page(
                    last_sync=last_sync,
                    page_token=page_token,
                    limit=limit
                )
                
                if not users:
                    break
                
                yield users
                
                if not next_token:
                    break
                    
                page_token = next_token
                
            except Exception as e:
                logger.error(f"Error fetching genius users page: {e}")
                break

    async def _fetch_users_page(self, last_sync: Optional[datetime] = None,
                               page_token: Optional[str] = None,
                               limit: int = 100) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch a single page of genius users with delta sync support"""
        
        # Define properties to retrieve
        properties = [
            "hs_object_id", "hs_createdate", "hs_lastmodifieddate", "createdAt", "updatedAt", "archived",
            "arrivy_user_id", "division", "division_id", "email", "job_title", "name", "title_id",
            "user_account_type", "user_id", "user_status_inactive"
        ]
        
        try:
            await self.authenticate()
            
            if last_sync:
                # Use search endpoint for incremental sync
                endpoint = f"{self.base_url}/crm/v3/objects/{self.object_type}/search"
                last_sync_str = last_sync.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                payload = {
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "hs_lastmodifieddate",
                            "operator": "GTE",
                            "value": last_sync_str
                        }]
                    }],
                    "properties": properties,
                    "limit": limit
                }
                
                if page_token:
                    payload["after"] = page_token
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(endpoint, headers=self.headers, json=payload) as response:
                        if response.status == 200:
                            response_data = await response.json()
                        else:
                            raw = await response.text()
                            raise Exception(f"HubSpot API error {response.status}: {raw}")
            else:
                # Use regular endpoint for full sync
                endpoint = f"{self.base_url}/crm/v3/objects/{self.object_type}/"
                params = {
                    "limit": str(limit),
                    "properties": ",".join(properties)
                }
                
                if page_token:
                    params["after"] = page_token
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(endpoint, headers=self.headers, params=params) as response:
                        if response.status == 200:
                            response_data = await response.json()
                        else:
                            raw = await response.text()
                            raise Exception(f"HubSpot API error {response.status}: {raw}")
            
            results = response_data.get("results", [])
            paging = response_data.get("paging", {})
            next_page = paging.get("next", {}).get("after")
            
            logger.info(f"Fetched {len(results)} genius users from HubSpot")
            return results, next_page
            
        except Exception as e:
            logger.error(f"Error fetching genius users page: {e}")
            return [], None

    async def fetch_all_users(self, batch_size=100, stdout=None, properties=None):
        """Legacy method - Async generator to fetch all Genius Users in batches (for backward compatibility)"""
        after = None
        while True:
            data = await self.fetch_users_batch(limit=batch_size, after=after, properties=properties)
            results = data.get("results", [])
            if not results:
                break
            yield results
            paging = data.get("paging", {})
            next_page = paging.get("next", {})
            after = next_page.get("after")
            if not after:
                break
