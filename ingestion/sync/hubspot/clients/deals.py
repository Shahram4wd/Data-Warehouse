"""
HubSpot deals API client
"""
import logging
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, AsyncGenerator
from .base import HubSpotBaseClient

logger = logging.getLogger(__name__)

class HubSpotDealsClient(HubSpotBaseClient):
    """HubSpot API client for deals"""
    
    async def fetch_deals(self, last_sync: Optional[datetime] = None,
                        limit: int = 100, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch deals from HubSpot with pagination"""
        page_token = None
        
        while True:
            try:
                deals, next_token = await self._fetch_deals_page(
                    last_sync=last_sync,
                    page_token=page_token,
                    limit=limit
                )
                
                if not deals:
                    break
                    
                yield deals
                
                if not next_token:
                    break
                    
                page_token = next_token
                
            except Exception as e:
                logger.error(f"Error fetching deals: {e}")
                break
    
    async def _fetch_deals_page(self, last_sync: Optional[datetime] = None,
                              page_token: Optional[str] = None,
                              limit: int = 100) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch a single page of deals"""
        
        # Define deal properties
        properties = [
            "dealname", "amount", "closedate", "createdate", "dealstage", "dealtype",
            "description", "hs_object_id", "hubspot_owner_id", "pipeline",
            "division", "priority", "hs_lastmodifieddate"
        ]
        
        try:
            if last_sync:
                # Use search endpoint for incremental sync
                endpoint = "crm/v3/objects/deals/search"
                last_sync_str = last_sync.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                payload = {
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "hs_lastmodifieddate",
                            "operator": "GT",
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
                endpoint = "crm/v3/objects/deals"
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
            
            logger.info(f"Fetched {len(results)} deals")
            return results, next_page
            
        except Exception as e:
            logger.error(f"Error fetching deals page: {e}")
            return [], None
