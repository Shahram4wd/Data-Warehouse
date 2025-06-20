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
                        "properties": properties,
                        "limit": limit
                    }
                    
                    # Add pagination token if provided
                    if page_token:
                        search_payload["after"] = page_token
                    
                    async with session.post(url, headers=self.headers, json=search_payload, timeout=60) as response:
                        return await self._process_response(response)
                        
                else:
                    # Use regular GET endpoint for full sync
                    url = f"{self.BASE_URL}/crm/v3/objects/{endpoint}"
                    params = {
                        "limit": str(limit),
                        "properties": ",".join(properties)
                    }
                    
                    if page_token:
                        params["after"] = page_token
                    
                    async with session.get(url, headers=self.headers, params=params, timeout=60) as response:
                        return await self._process_response(response)
                        
            except Exception as e:
                logger.error(f"Error fetching page: {str(e)}")
                return [], None

    async def _process_response(self, response):
        """Process the HTTP response and extract results and pagination info."""
        status = response.status
        logger.info(f"Response status: {status}")
        
        if status != 200:
            response_text = await response.text()
            logger.error(f"Error response: {response_text[:500]}")
            return [], None
        
        data = await response.json()
        results = data.get("results", [])
        logger.info(f"Got {len(results)} results")
        
        # Get next page token if available
        paging = data.get("paging", {})
        next_page = paging.get("next", {}).get("after")
        if next_page:
            logger.info(f"Next page token: {next_page}")
        
        return results, next_page

    async def get_appointments_page(
        self, 
        last_sync: Optional[datetime] = None, 
        page_token: Optional[str] = None,
        limit: int = 100
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch a single page of appointments from HubSpot custom object 0-421."""
        
        # Create a fresh session for each call
        async with aiohttp.ClientSession() as session:            # All properties for the custom appointment object (from API documentation)
            properties = [
                "add_date", "add_user_id", "address1", "address2", "appointment_id",
                "appointment_response", "appointment_services", "appointment_status",
                "arrivy_appt_date", "arrivy_confirm_date", "arrivy_confirm_user",
                "arrivy_created_by", "arrivy_object_id", "arrivy_status", "arrivy_user",
                "arrivy_user_divison_id", "arrivy_user_external_id", "arrivy_username",
                "assign_date", "canvasser", "canvasser_email", "canvasser_id", "city",
                "complete_date", "complete_outcome_id", "complete_outcome_id_text",
                "complete_user_id", "confirm_date", "confirm_user_id", "confirm_with",
                "date", "division_id", "duration", "email", "error_details", "first_name",
                "genius_appointment_id", 
                # HubSpot system fields
                "hs_all_accessible_team_ids", "hs_all_assigned_business_unit_ids",
                "hs_all_owner_ids", "hs_all_team_ids", "hs_appointment_end", 
                "hs_appointment_name", "hs_appointment_start", "hs_created_by_user_id",
                "hs_createdate", "hs_duration", "hs_lastmodifieddate", "hs_merged_object_ids",
                "hs_object_id", "hs_object_source", "hs_object_source_detail_1",
                "hs_object_source_detail_2", "hs_object_source_detail_3", "hs_object_source_id",
                "hs_object_source_label", "hs_object_source_user_id", "hs_owning_teams",
                "hs_pipeline", "hs_pipeline_stage", "hs_read_only", "hs_shared_team_ids",
                "hs_shared_user_ids", "hs_unique_creation_key", "hs_updated_by_user_id",
                "hs_user_ids_of_all_notification_followers", "hs_user_ids_of_all_notification_unfollowers",
                "hs_user_ids_of_all_owners", "hs_was_imported",
                # Custom fields continued
                "hscontact_id", "hubspot_owner_assigneddate", "hubspot_owner_id",
                "hubspot_team_id", "is_complete", "last_name", "lead_services",
                "leap_estimate_id", "log", "marketing_task_id", "marketsharp_appt_type",
                "marketsharp_id", "notes", "phone1", "phone2", "primary_source",
                "product_interest_primary", "product_interest_secondary", "prospect_id",
                "prospect_source_id", "salespro_both_homeowners", "salespro_deadline",
                "salespro_deposit_type", "salespro_fileurl_contract", "salespro_fileurl_estimate",
                "salespro_financing", "salespro_job_size", "salespro_job_type",
                "salespro_last_price_offered", "salespro_notes", "salespro_one_year_price",
                "salespro_preferred_payment", "salespro_requested_start", "salespro_result",
                "salespro_result_notes", "salespro_result_reason_demo", "salespro_result_reason_no_demo",
                "secondary_source", "spouses_present", "state", "tester_test", "time",
                "title", "type_id", "type_id_text", "user_id", "year_built", "zip"
            ]
            
            try:
                # Use search endpoint for appointments (custom object 0-421)
                url = f"{self.BASE_URL}/crm/v3/objects/0-421/search"
                
                payload = {
                    "filterGroups": [],
                    "properties": properties,
                    "limit": limit
                }
                
                # Add date filter if last_sync is provided
                if last_sync:
                    last_sync_str = last_sync.strftime('%Y-%m-%dT%H:%M:%SZ')
                    payload["filterGroups"] = [{
                        "filters": [{
                            "propertyName": "hs_lastmodifieddate",
                            "operator": "GTE",
                            "value": last_sync_str
                        }]
                    }]
                
                # Add pagination if provided
                if page_token:
                    payload["after"] = page_token
                
                logger.info(f"Fetching appointments from {url}")
                logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
                
                async with session.post(url, headers=self.headers, json=payload) as response:
                    status = response.status
                    logger.info(f"Response status: {status}")
                    
                    if status != 200:
                        response_text = await response.text()
                        logger.error(f"Error response: {response_text[:500]}")
                        return [], None
                    
                    data = await response.json()
                    results = data.get("results", [])
                    logger.info(f"Got {len(results)} appointment results")
                    
                    # Get next page token if available
                    paging = data.get("paging", {})
                    next_page = paging.get("next", {}).get("after")
                    if next_page:
                        logger.info(f"Next page token: {next_page}")
                    
                    return results, next_page
                    
            except Exception as e:
                logger.error(f"Error fetching appointments: {str(e)}")
                return [], None
