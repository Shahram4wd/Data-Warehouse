import logging
import json
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
import aiohttp
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
        logger.info(f"HubspotClient initialized with token: {self.api_token[:5]}...{self.api_token[-5:]}")
    
    async def get_page(
        self, 
        endpoint: str, 
        last_sync: Optional[datetime] = None, 
        page_token: Optional[str] = None,
        limit: int = 100
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch a single page of contacts from HubSpot API."""
        
        try:
            # Use search endpoint if we need to filter by date
            if last_sync:
                url = f"{self.BASE_URL}/crm/v3/objects/{endpoint}/search"
                
                # Format the date for HubSpot API
                last_sync_str = last_sync.strftime('%Y-%m-%dT%H:%M:%SZ')
                logger.info(f"Filtering by lastmodifieddate > {last_sync_str}")
                
                # Prepare search payload
                search_payload = {
                    "filterGroups": [
                        {
                            "filters": [
                                {
                                    "propertyName": "lastmodifieddate",
                                    "operator": "GT",
                                    "value": last_sync_str
                                }
                            ]
                        }
                    ],
                    "properties": [
                        "firstname", "lastname", "email", "phone", "address", "city", "state", "zip",
                        "hs_object_id", "createdate", "lastmodifieddate", "campaign_name", "division",
                        "marketsharp_id", "hs_google_click_id", "original_lead_source", 
                        "original_lead_source_created", "adgroupid", "ap_leadid", "campaign_content",
                        "clickcheck", "clicktype", "comments", "lead_salesrabbit_lead_id", "msm_source",
                        "price", "reference_code", "search_terms", "tier", "trustedform_cert_url",
                        "vendorleadid", "vertical"
                    ],
                    "limit": limit
                }
                
                # Add pagination token if provided
                if page_token:
                    search_payload["after"] = page_token
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=self.headers, json=search_payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            results = data.get('results', [])
                            next_token = data.get('paging', {}).get('next', {}).get('after')
                            return results, next_token
                        else:
                            error_text = await response.text()
                            logger.error(f"Error fetching page: {response.status} - {error_text}")
                            return [], None
                            
            else:
                # Use regular GET endpoint for full sync
                url = f"{self.BASE_URL}/crm/v3/objects/{endpoint}"
                params = {
                    "limit": str(limit),
                    "properties": ",".join([
                        "firstname", "lastname", "email", "phone", "address", "city", "state", "zip",
                        "hs_object_id", "createdate", "lastmodifieddate", "campaign_name", "division",
                        "marketsharp_id", "hs_google_click_id", "original_lead_source", 
                        "original_lead_source_created", "adgroupid", "ap_leadid", "campaign_content",
                        "clickcheck", "clicktype", "comments", "lead_salesrabbit_lead_id", "msm_source",
                        "price", "reference_code", "search_terms", "tier", "trustedform_cert_url",
                        "vendorleadid", "vertical"
                    ])
                }
                
                if page_token:
                    params["after"] = page_token
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=self.headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            results = data.get('results', [])
                            next_token = data.get('paging', {}).get('next', {}).get('after')
                            return results, next_token
                        else:
                            error_text = await response.text()
                            logger.error(f"Error fetching page: {response.status} - {error_text}")
                            return [], None
                            
        except Exception as e:
            logger.error(f"Error fetching page: {str(e)}")
            return [], None
