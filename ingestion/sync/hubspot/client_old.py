"""
HubSpot API client implementation
"""
import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, List, Dict, Any, AsyncGenerator
import aiohttp
from django.conf import settings
from ingestion.base.client import BaseAPIClient
from ingestion.base.exceptions import APIException, RateLimitException

logger = logging.getLogger(__name__)

class HubSpotClient(BaseAPIClient):
    """HubSpot API client"""
    
    def __init__(self, api_token=None):
        super().__init__(base_url="https://api.hubapi.com", timeout=60)
        self.api_token = api_token or settings.HUBSPOT_API_TOKEN
        
    async def authenticate(self) -> None:
        """Set up authentication headers"""
        self.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        })
        logger.info(f"HubSpot client initialized with token: {self.api_token[:5]}...{self.api_token[-5:]}")
    
    def get_rate_limit_headers(self) -> Dict[str, str]:
        """Return HubSpot rate limit headers"""
        return {
            'X-HubSpot-RateLimit-Daily': 'X-HubSpot-RateLimit-Daily',
            'X-HubSpot-RateLimit-Daily-Remaining': 'X-HubSpot-RateLimit-Daily-Remaining',
            'X-HubSpot-RateLimit-Secondly': 'X-HubSpot-RateLimit-Secondly',
            'X-HubSpot-RateLimit-Secondly-Remaining': 'X-HubSpot-RateLimit-Secondly-Remaining'
        }
    
    async def fetch_contacts(self, last_sync: Optional[datetime] = None, 
                           limit: int = 100, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch contacts from HubSpot API"""
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
    
    async def fetch_appointments(self, last_sync: Optional[datetime] = None,
                               limit: int = 100, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch appointments from HubSpot custom object 0-421"""
        page_token = None
        
        while True:
            try:
                appointments, next_token = await self._fetch_appointments_page(
                    last_sync=last_sync,
                    page_token=page_token,
                    limit=limit
                )
                
                if not appointments:
                    break
                    
                yield appointments
                
                if not next_token:
                    break
                    
                page_token = next_token
                
            except Exception as e:
                logger.error(f"Error fetching appointments: {e}")
                break
    
    async def _fetch_appointments_page(self, last_sync: Optional[datetime] = None,
                                     page_token: Optional[str] = None,
                                     limit: int = 100) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch a single page of appointments from custom object 0-421"""
        
        # Define all appointment properties
        properties = [
            "appointment_id", "genius_appointment_id", "marketsharp_id",
            "hs_appointment_name", "hs_appointment_start", "hs_appointment_end",
            "hs_duration", "hs_object_id", "hs_createdate", "hs_lastmodifieddate",
            "hs_pipeline", "hs_pipeline_stage",
            # Contact info
            "first_name", "last_name", "email", "phone1", "phone2",
            "address1", "address2", "city", "state", "zip",
            # Appointment details
            "date", "time", "duration", "appointment_status", "appointment_response",
            "is_complete", "appointment_services", "lead_services",
            "type_id", "type_id_text", "marketsharp_appt_type",
            # User and assignment
            "user_id", "canvasser", "canvasser_id", "canvasser_email",
            "hubspot_owner_id", "hubspot_owner_assigneddate", "hubspot_team_id",
            "division_id", "primary_source", "secondary_source",
            "prospect_id", "prospect_source_id", "hscontact_id",
            # Completion and confirmation
            "complete_date", "complete_outcome_id", "complete_outcome_id_text",
            "complete_user_id", "confirm_date", "confirm_user_id", "confirm_with",
            "assign_date", "add_date", "add_user_id",
            # Integration fields
            "arrivy_appt_date", "arrivy_confirm_date", "arrivy_confirm_user",
            "arrivy_created_by", "arrivy_object_id", "arrivy_status", "arrivy_user",
            "arrivy_user_divison_id", "arrivy_user_external_id", "arrivy_username",
            # SalesPro fields
            "salespro_both_homeowners", "salespro_deadline", "salespro_deposit_type",
            "salespro_fileurl_contract", "salespro_fileurl_estimate", "salespro_financing",
            "salespro_job_size", "salespro_job_type", "salespro_last_price_offered",
            "salespro_notes", "salespro_one_year_price", "salespro_preferred_payment",
            "salespro_requested_start", "salespro_result", "salespro_result_notes",
            "salespro_result_reason_demo", "salespro_result_reason_no_demo",
            # Additional fields
            "notes", "log", "title", "marketing_task_id", "leap_estimate_id",
            "spouses_present", "year_built", "error_details", "tester_test",
            # HubSpot system fields
            "hs_all_accessible_team_ids", "hs_all_assigned_business_unit_ids",
            "hs_all_owner_ids", "hs_all_team_ids", "hs_created_by_user_id",
            "hs_merged_object_ids", "hs_object_source", "hs_object_source_detail_1",
            "hs_object_source_detail_2", "hs_object_source_detail_3", "hs_object_source_id",
            "hs_object_source_label", "hs_object_source_user_id", "hs_owning_teams",
            "hs_read_only", "hs_shared_team_ids", "hs_shared_user_ids",
            "hs_unique_creation_key", "hs_updated_by_user_id",
            "hs_user_ids_of_all_notification_followers", "hs_user_ids_of_all_notification_unfollowers",
            "hs_user_ids_of_all_owners", "hs_was_imported"
        ]
        
        try:
            if last_sync:
                # Use search endpoint for incremental sync
                endpoint = "crm/v3/objects/0-421/search"
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
                endpoint = "crm/v3/objects/0-421"
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
            
            logger.info(f"Fetched {len(results)} appointments")
            return results, next_page
            
        except Exception as e:
            logger.error(f"Error fetching appointments page: {e}")
            return [], None
    
    async def fetch_divisions(self, last_sync: Optional[datetime] = None,
                            limit: int = 100, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch divisions from HubSpot custom object 2-37778609"""
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
            # HubSpot system fields
            "hs_object_id", "hs_createdate", "hs_lastmodifieddate", "hs_pipeline",
            "hs_pipeline_stage", "hs_all_accessible_team_ids", "hs_all_assigned_business_unit_ids",
            "hs_all_owner_ids", "hs_all_team_ids", "hs_created_by_user_id",
            "hs_merged_object_ids", "hs_object_source", "hs_object_source_detail_1",
            "hs_object_source_detail_2", "hs_object_source_detail_3", "hs_object_source_id",
            "hs_object_source_label", "hs_object_source_user_id", "hs_owning_teams",
            "hs_read_only", "hs_shared_team_ids", "hs_shared_user_ids",
            "hs_unique_creation_key", "hs_updated_by_user_id",
            "hs_user_ids_of_all_notification_followers", "hs_user_ids_of_all_notification_unfollowers",
            "hs_user_ids_of_all_owners", "hs_was_imported"
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
    
    async def fetch_deals(self, last_sync: Optional[datetime] = None,
                        limit: int = 100, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch deals from HubSpot"""
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
            "division", "priority"
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

    async def fetch_associations(self, from_object_type: str, to_object_type: str,
                               object_ids: List[str], **kwargs) -> List[Dict[str, Any]]:
        """Fetch associations between HubSpot objects"""
        try:
            # Use batch association endpoint
            endpoint = f"crm/v4/associations/{from_object_type}/{to_object_type}/batch/read"
            
            payload = {
                "inputs": [{"id": obj_id} for obj_id in object_ids[:100]]  # Batch limit
            }
            
            response_data = await self.make_request("POST", endpoint, json=payload)
            results = response_data.get("results", [])
            
            logger.info(f"Fetched {len(results)} associations from {from_object_type} to {to_object_type}")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching associations: {e}")
            return []
