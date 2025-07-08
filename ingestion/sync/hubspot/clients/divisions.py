"""
HubSpot divisions API client
"""
import logging
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, AsyncGenerator
from .base import HubSpotBaseClient

logger = logging.getLogger(__name__)

class HubSpotDivisionsClient(HubSpotBaseClient):
    """HubSpot API client for divisions (custom object 2-37778609)"""
    
    async def fetch_divisions(self, last_sync: Optional[datetime] = None,
                            limit: int = 100, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch divisions from HubSpot custom object 2-37778609 with pagination"""
        page_token = None
        
        while True:
            try:
                divisions, next_token = await self._fetch_divisions_page(
                    last_sync=last_sync,
                    page_token=page_token,
                    limit=limit
                )
                
                if not divisions:
                    break
                    
                yield divisions
                
                if not next_token:
                    break
                    
                page_token = next_token
                
            except Exception as e:
                logger.error(f"Error fetching divisions: {e}")
                break
    
    async def _fetch_divisions_page(self, last_sync: Optional[datetime] = None,
                                  page_token: Optional[str] = None,
                                  limit: int = 100) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch a single page of divisions from custom object 2-37778609"""
        
        # Define division properties
        properties = [
            "division_name", "division_label", "label", "division_code", "code",
            "status", "region", "manager_name", "manager_email", "phone",
            "address1", "address2", "city", "state", "zip",
            "hs_object_id", "hs_createdate", "hs_lastmodifieddate"
        ]
        
        try:
            if last_sync:
                # Use search endpoint for incremental sync
                endpoint = "crm/v3/objects/2-37778609/search"
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
                
                response_data = await self.make_request("POST", endpoint, json=payload)
            else:
                # Use regular endpoint for full sync
                endpoint = "crm/v3/objects/2-37778609"
                params = {
                    "limit": str(limit),
                    "properties": ",".join(properties)
                }
                
                if page_token:
                    params["after"] = page_token
                
                response_data = await self.make_request("GET", endpoint, params=params)
            
            results = response_data.get("results", [])
            paging = response_data.get("paging", {})
            next_page = paging.get("next", {}).get("after")
            
            logger.info(f"Fetched {len(results)} divisions")
            return results, next_page
            
        except Exception as e:
            logger.error(f"Error fetching divisions page: {e}")
            return [], None
