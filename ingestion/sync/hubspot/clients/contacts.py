"""
HubSpot contacts API client
"""
import logging
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, AsyncGenerator
from .base import HubSpotBaseClient

logger = logging.getLogger(__name__)

class HubSpotContactsClient(HubSpotBaseClient):
    """HubSpot API client for contacts"""
    
    async def fetch_contacts(self, last_sync: Optional[datetime] = None, 
                           limit: int = 100, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch contacts from HubSpot API with pagination"""
        page_token = None
        
        while True:
            try:
                contacts, next_token = await self._fetch_contacts_page(
                    last_sync=last_sync,
                    page_token=page_token,
                    limit=limit
                )
                
                if not contacts:
                    break
                    
                yield contacts
                
                if not next_token:
                    break
                    
                page_token = next_token
                
            except Exception as e:
                logger.error(f"Error fetching contacts: {e}")
                break
    
    async def _fetch_contacts_page(self, last_sync: Optional[datetime] = None,
                                 page_token: Optional[str] = None,
                                 limit: int = 100) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch a single page of contacts"""
        
        # Define properties to retrieve
        properties = [
            "firstname", "lastname", "email", "phone", "address", "city", "state", "zip",
            "createdate", "lastmodifieddate", "campaign_name", "hs_google_click_id",
            "original_lead_source", "division", "marketsharp_id", "adgroupid", "ap_leadid",
            "campaign_content", "clickcheck", "clicktype", "comments", "lead_salesrabbit_lead_id",
            "msm_source", "original_lead_source_created", "price", "reference_code",
            "search_terms", "tier", "trustedform_cert_url", "vendorleadid", "vertical",
            "hs_object_id"
        ]
        
        try:
            if last_sync:
                # Use search endpoint for incremental sync
                endpoint = "crm/v3/objects/contacts/search"
                last_sync_str = last_sync.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                payload = {
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "lastmodifieddate",
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
                endpoint = "crm/v3/objects/contacts"
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
            
            logger.info(f"Fetched {len(results)} contacts")
            return results, next_page
            
        except Exception as e:
            logger.error(f"Error fetching contacts page: {e}")
            return [], None
