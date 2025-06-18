import logging
import json
from datetime import datetime
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
        print(f"HubspotClient initialized with token: {self.api_token[:5]}...{self.api_token[-5:]}")
    
    async def get_page(self, endpoint, last_sync=None, page_token=None):
        """Get a single page of data from a HubSpot endpoint."""
        # Create a fresh session for each call
        async with aiohttp.ClientSession() as session:
            # Set properties to retrieve
            properties = [
                "firstname", "lastname", "email", "phone", "address", "city", "state", "zip",
                "createdate", "lastmodifieddate", "campaign_name", "hs_google_click_id",
                "original_lead_source", "division", "marketsharp_id", "adgroupid", "ap_leadid",
                "campaign_content", "clickcheck", "clicktype", "comments", "lead_salesrabbit_lead_id",
                "msm_source", "original_lead_source_created", "price", "reference_code",
                "search_terms", "tier", "trustedform_cert_url", "vendorleadid", "vertical",
                "hs_object_id"
            ]
            
            # If we need filtering, use the search API with POST
            if last_sync:
                last_sync_str = last_sync.strftime("%Y-%m-%dT%H:%M:%SZ")
                print(f"Filtering by lastmodifieddate > {last_sync_str}")
                
                url = f"{self.BASE_URL}/crm/v3/objects/{endpoint}/search"
                
                # Build POST body for search API
                search_body = {
                    "limit": 100,
                    "properties": properties,
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "lastmodifieddate",
                            "operator": "GT",
                            "value": last_sync_str
                        }]
                    }]
                }
                
                # Add page token if provided
                if page_token:
                    search_body["after"] = page_token
                
                try:
                    async with session.post(url, headers=self.headers, json=search_body, timeout=60) as response:
                        return await self._process_response(response)
                except Exception as e:
                    print(f"Error fetching page: {str(e)}")
                    return None, None
            else:
                # Use regular GET API for no filtering
                params = {
                    "limit": 100,
                    "properties": properties
                }
                
                # Add page token if provided
                if page_token:
                    params["after"] = page_token
                
                url = f"{self.BASE_URL}/crm/v3/objects/{endpoint}"
                
                try:
                    async with session.get(url, headers=self.headers, params=params, timeout=60) as response:
                        return await self._process_response(response)
                except Exception as e:
                    print(f"Error fetching page: {str(e)}")
                    return None, None

    async def _process_response(self, response):
        """Process the HTTP response and extract results and pagination info."""
        status = response.status
        print(f"Response status: {status}")
        
        if status != 200:
            response_text = await response.text()
            print(f"Error response: {response_text[:500]}")
            return None, None
        
        data = await response.json()
        results = data.get("results", [])
        print(f"Got {len(results)} results")
        
        # Get next page token if available
        paging = data.get("paging", {})
        next_page = paging.get("next", {}).get("after")
        if next_page:
            print(f"Next page token: {next_page}")
        
        return results, next_page
