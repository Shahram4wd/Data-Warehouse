import logging
import json
from datetime import datetime, timedelta, timezone
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

    async def get_appointments_chunked(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        chunk_days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Fetch all appointments using date-based chunking to overcome HubSpot's 10,000 record limit.
        
        Args:
            start_date: Start date for fetching appointments
            end_date: End date for fetching appointments  
            chunk_days: Number of days per chunk (default 30)
            
        Returns:
            List of all appointment records
        """
        all_appointments = []
        
        if not start_date:
            # Default to 2018-01-01 as mentioned in the user request
            start_date = datetime(2018, 1, 1, tzinfo=timezone.utc)
        
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        logger.info(f"Fetching appointments from {start_date} to {end_date} using {chunk_days}-day chunks")
        
        current_date = start_date
        chunk_num = 1
        
        while current_date < end_date:
            chunk_end = min(current_date + timedelta(days=chunk_days), end_date)
            
            logger.info(f"Processing chunk {chunk_num}: {current_date.strftime('%Y-%m-%d')} to {chunk_end.strftime('%Y-%m-%d')}")
            
            # Fetch appointments for this date range
            chunk_appointments = await self._get_appointments_for_date_range(current_date, chunk_end)
            all_appointments.extend(chunk_appointments)
            
            logger.info(f"Chunk {chunk_num}: Found {len(chunk_appointments)} appointments (Total: {len(all_appointments)})")
            
            current_date = chunk_end
            chunk_num += 1
        
        logger.info(f"Completed chunked fetch: {len(all_appointments)} total appointments")
        return all_appointments

    async def _get_appointments_for_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Fetch all appointments for a specific date range using pagination.
        
        Args:
            start_date: Start date for the range
            end_date: End date for the range
            
        Returns:
            List of appointment records for the date range
        """
        appointments = []
        page_token = None
        page_num = 1
        
        while True:
            logger.debug(f"Fetching page {page_num} for date range {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            # Fetch page with date range filter
            page_appointments, next_page_token = await self._get_appointments_page_with_date_range(
                start_date, end_date, page_token, limit=100
            )
            
            if not page_appointments:
                logger.debug(f"No more appointments found for date range")
                break
            
            appointments.extend(page_appointments)
            logger.debug(f"Page {page_num}: Got {len(page_appointments)} appointments (Range total: {len(appointments)})")
            
            if not next_page_token:
                logger.debug(f"Reached end of pagination for date range")
                break
            
            page_token = next_page_token
            page_num += 1
            
            # Safety check to prevent infinite loops
            if page_num > 1000:  # Should never need this many pages for a 30-day chunk
                logger.warning(f"Breaking pagination loop at page {page_num} for safety")
                break
        
        return appointments

    async def _get_appointments_page_with_date_range(
        self,
        start_date: datetime,
        end_date: datetime, 
        page_token: Optional[str] = None,
        limit: int = 100
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Fetch a single page of appointments with date range filtering.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            page_token: Pagination token
            limit: Number of records per page
            
        Returns:
            Tuple of (appointments list, next_page_token)
        """
        async with aiohttp.ClientSession() as session:
            # Same properties as the main get_appointments_page method
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
                url = f"{self.BASE_URL}/crm/v3/objects/0-421/search"
                
                # Create date range filter
                start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                end_date_str = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                payload = {
                    "filterGroups": [{
                        "filters": [
                            {
                                "propertyName": "hs_createdate",
                                "operator": "GTE",
                                "value": start_date_str
                            },
                            {
                                "propertyName": "hs_createdate", 
                                "operator": "LTE",
                                "value": end_date_str
                            }
                        ]
                    }],
                    "properties": properties,
                    "limit": limit
                }
                
                # Add pagination if provided
                if page_token:
                    payload["after"] = page_token
                
                logger.debug(f"Fetching appointments with date range filter: {start_date_str} to {end_date_str}")
                
                async with session.post(url, headers=self.headers, json=payload) as response:
                    status = response.status
                    
                    if status != 200:
                        response_text = await response.text()
                        logger.error(f"Error response for date range {start_date_str} to {end_date_str}: {response_text[:500]}")
                        return [], None
                    
                    data = await response.json()
                    results = data.get("results", [])
                    
                    # Get next page token if available
                    paging = data.get("paging", {})
                    next_page = paging.get("next", {}).get("after")
                    
                    return results, next_page
                    
            except Exception as e:
                logger.error(f"Error fetching appointments for date range {start_date_str} to {end_date_str}: {str(e)}")
                return [], None

    async def fetch_appointments_in_batches(self, batch_size: int = 100):
        """Fetch appointments in batches and process them efficiently."""
        all_appointments = []
        page_token = None
        batch_num = 1

        while True:
            logger.info(f"Fetching batch {batch_num} with batch size {batch_size}")
            appointments, next_page_token = await self.get_appointments_page(page_token=page_token, limit=batch_size)

            if not appointments:
                logger.info("No more appointments to fetch.")
                break

            all_appointments.extend(appointments)
            logger.info(f"Batch {batch_num}: Fetched {len(appointments)} appointments (Total: {len(all_appointments)})")

            if not next_page_token:
                logger.info("Reached the end of pagination.")
                break

            page_token = next_page_token
            batch_num += 1

        logger.info(f"Completed fetching appointments. Total: {len(all_appointments)}")
        return all_appointments

    async def process_appointments_bulk(self, appointments: List[Dict[str, Any]]):
        """Process appointments in bulk to optimize database operations."""
        from ingestion.models.hubspot import HubspotAppointment  # Import model here to avoid circular imports
        from django.db import transaction

        BATCH_SIZE = 500  # Ensure a larger batch size for efficiency
        to_create = []
        to_update = []

        existing_appointments = HubspotAppointment.objects.in_bulk([appt['hs_object_id'] for appt in appointments])

        for appt in appointments:
            appt_id = appt['hs_object_id']
            if appt_id in existing_appointments:
                # Update existing record
                existing = existing_appointments[appt_id]
                for field, value in appt.items():
                    setattr(existing, field, value)
                to_update.append(existing)
            else:
                # Create new record
                to_create.append(HubspotAppointment(**appt))

            # Process in larger batches
            if len(to_create) >= BATCH_SIZE:
                with transaction.atomic():
                    HubspotAppointment.objects.bulk_create(to_create, ignore_conflicts=True)
                to_create.clear()

            if len(to_update) >= BATCH_SIZE:
                with transaction.atomic():
                    HubspotAppointment.objects.bulk_update(to_update, fields=appt.keys())
                to_update.clear()

        # Final batch processing
        if to_create:
            with transaction.atomic():
                HubspotAppointment.objects.bulk_create(to_create, ignore_conflicts=True)

        if to_update:
            with transaction.atomic():
                HubspotAppointment.objects.bulk_update(to_update, fields=appt.keys())

        logger.info(f"Processed {len(appointments)} appointments in bulk.")

    async def fetch_and_process_appointments(self, batch_size: int = 500):
        """Fetch and process appointments in batches."""
        all_appointments = []
        page_token = None
        batch_num = 1

        while True:
            logger.info(f"Fetching batch {batch_num} with batch size {batch_size}")
            appointments, next_page_token = await self.get_appointments_page(page_token=page_token, limit=batch_size)

            if not appointments:
                logger.info("No more appointments to fetch.")
                break

            # Process the fetched appointments in bulk
            await self.process_appointments_bulk(appointments)
            all_appointments.extend(appointments)

            logger.info(f"Batch {batch_num}: Processed {len(appointments)} appointments (Total: {len(all_appointments)})")

            if not next_page_token:
                logger.info("Reached the end of pagination.")
                break

            page_token = next_page_token
            batch_num += 1

        logger.info(f"Completed fetching and processing appointments. Total: {len(all_appointments)}")
        return all_appointments

    async def get_associations(
        self,
        from_object: str,
        to_object: str,
        page_token: Optional[str] = None,
        limit: int = 100
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """List associations between two HubSpot object types using v3 API."""
        # Use the v3 associations endpoint
        url = f"{self.BASE_URL}/crm/v3/associations/{from_object}/{to_object}"
        params = {"limit": str(limit)}
        if page_token:
            params["after"] = page_token
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers, params=params, timeout=60) as response:
                    return await self._process_response(response)
            except Exception as e:
                logger.error(f"Error fetching associations: {str(e)}")
                return [], None
    
    async def get_object_associations(
        self,
        from_object: str,
        object_id: str,
        to_object: str,
        page_token: Optional[str] = None,
        limit: int = 100
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch associations for a specific object via v3 associations endpoint."""
        url = f"{self.BASE_URL}/crm/v3/objects/{from_object}/{object_id}/associations/{to_object}"
        params = {"limit": str(limit)}
        if page_token:
            params["after"] = page_token
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers, params=params, timeout=60) as response:
                    return await self._process_response(response)
            except Exception as e:
                logger.error(f"Error fetching object associations: {str(e)}")
                return [], None
    
    async def get_bulk_associations(self, from_object_type: str, to_object_type: str, inputs: List[str]) -> List[Dict[str, Any]]:
        """Fetch bulk associations between two object types using HubSpot API v4."""
        url = f"{self.BASE_URL}/crm/v4/associations/{from_object_type}/{to_object_type}/batch/read"
        payload = {"inputs": [{"id": obj_id} for obj_id in inputs]}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=self.headers, json=payload, timeout=60) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        logger.error(f"Error fetching bulk associations: {response_text[:500]}")
                        return []

                    data = await response.json()
                    results = data.get("results", [])
                    logger.info(f"Fetched {len(results)} associations.")
                    return results

            except Exception as e:
                logger.error(f"Exception during bulk association fetch: {str(e)}")
                return []

    async def get_custom_object_page(
        self, 
        object_type: str,
        last_sync: Optional[datetime] = None, 
        page_token: Optional[str] = None,
        limit: int = 100
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch a single page from a HubSpot custom object."""
        
        # Create a fresh session for each call
        async with aiohttp.ClientSession() as session:
            # Set properties to retrieve for divisions
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
                # Use search endpoint if we need to filter by date
                if last_sync:
                    url = f"{self.BASE_URL}/crm/v3/objects/{object_type}/search"
                    
                    # Format the date for HubSpot API
                    last_sync_str = last_sync.strftime('%Y-%m-%dT%H:%M:%SZ')
                    
                    payload = {
                        "filterGroups": [
                            {
                                "filters": [
                                    {
                                        "propertyName": "hs_lastmodifieddate",
                                        "operator": "GTE",
                                        "value": last_sync_str
                                    }
                                ]
                            }
                        ],
                        "properties": properties,
                        "limit": limit
                    }
                    
                    if page_token:
                        payload["after"] = page_token
                    
                    logger.info(f"Fetching custom object {object_type} with search payload: {json.dumps(payload, indent=2)[:500]}")
                    
                    async with session.post(url, headers=self.headers, json=payload, timeout=120) as response:
                        status = response.status
                        logger.info(f"Search response status: {status}")
                        
                        if status != 200:
                            response_text = await response.text()
                            logger.error(f"Error response: {response_text[:500]}")
                            return [], None
                        
                        data = await response.json()
                        results = data.get("results", [])
                        logger.info(f"Got {len(results)} custom object results")
                        
                        # Get next page token if available
                        paging = data.get("paging", {})
                        next_page = paging.get("next", {}).get("after")
                        if next_page:
                            logger.info(f"Next page token: {next_page}")
                        
                        return results, next_page
                
                else:
                    # Use regular get endpoint for full sync
                    url = f"{self.BASE_URL}/crm/v3/objects/{object_type}"
                    params = {
                        "properties": ",".join(properties),
                        "limit": limit
                    }
                    
                    if page_token:
                        params["after"] = page_token
                    
                    logger.info(f"Fetching custom object {object_type} with params: {params}")
                    
                    async with session.get(url, headers=self.headers, params=params, timeout=120) as response:
                        status = response.status
                        logger.info(f"Response status: {status}")
                        
                        if status != 200:
                            response_text = await response.text()
                            logger.error(f"Error response: {response_text[:500]}")
                            return [], None
                        
                        data = await response.json()
                        results = data.get("results", [])
                        logger.info(f"Got {len(results)} custom object results")
                        
                        # Get next page token if available
                        paging = data.get("paging", {})
                        next_page = paging.get("next", {}).get("after")
                        if next_page:
                            logger.info(f"Next page token: {next_page}")
                        
                        return results, next_page
                        
            except Exception as e:
                logger.error(f"Exception during custom object fetch: {str(e)}")
                return [], None

    async def get_associations_page(
        self, 
        from_object_type: str,
        to_object_type: str,
        inputs: List[str] = None,
        page_token: Optional[str] = None,
        batch_size: int = 100,
        association_type_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fetch a single page of associations between two object types from HubSpot API.
        
        Args:
            from_object_type: Source object type (e.g., 'contacts')
            to_object_type: Target object type (e.g., '2-37778609' for divisions)
            page_token: Pagination token for next page
            batch_size: Number of associations per page
            association_type_id: Specific association type ID to filter by
            
        Returns:
            Dictionary containing results and pagination info
        """
        async with aiohttp.ClientSession() as session:
            try:
                # Use the v4 batch read endpoint
                url = f"{self.BASE_URL}/crm/v4/associations/{from_object_type}/{to_object_type}/batch/read"
                
                # Prepare inputs - if none provided, return empty results
                if not inputs:
                    logger.warning("No inputs provided for associations batch read")
                    return {"results": [], "paging": {}}
                
                # Build payload with inputs
                payload = {
                    "inputs": [{"id": input_id} for input_id in inputs[:batch_size]]
                }
                
                if association_type_id:
                    logger.info(f"Fetching associations from {from_object_type} to {to_object_type} with type ID {association_type_id}")
                else:
                    logger.info(f"Fetching associations from {from_object_type} to {to_object_type}")
                
                if page_token:
                    payload["after"] = page_token
                
                logger.debug(f"Associations payload: {json.dumps(payload, indent=2)}")
                
                async with session.post(url, headers=self.headers, json=payload, timeout=120) as response:
                    status = response.status
                    logger.info(f"Associations response status: {status}")
                    
                    if status not in [200, 207]:  # 207 is Multi-Status for batch operations
                        response_text = await response.text()
                        logger.error(f"Error response: {response_text[:500]}")
                        return {"results": [], "paging": {}}
                    
                    data = await response.json()
                    results = data.get("results", [])
                    logger.info(f"Got {len(results)} association results")
                    
                    return data
                    
            except Exception as e:
                logger.error(f"Exception during associations fetch: {str(e)}")
                return {"results": [], "paging": {}}
        
    async def get_association_labels(
        self,
        from_object_type: str,
        to_object_type: str
    ) -> List[Dict[str, Any]]:
        """Get all association labels between two object types."""
        url = f"{self.BASE_URL}/crm/v4/associations/{from_object_type}/{to_object_type}/labels"
        
        async with aiohttp.ClientSession() as session:
            try:
                logger.info(f"Fetching association labels from {from_object_type} to {to_object_type}")
                async with session.get(url, headers=self.headers) as response:
                    status = response.status
                    logger.info(f"Association labels response status: {status}")
                    
                    if status != 200:
                        response_text = await response.text()
                        logger.error(f"Error response: {response_text[:500]}")
                        return []
                    
                    data = await response.json()
                    results = data.get("results", [])
                    logger.info(f"Got {len(results)} association labels")
                    
                    return results
                    
            except Exception as e:
                logger.error(f"Error fetching association labels: {str(e)}")
                return []
