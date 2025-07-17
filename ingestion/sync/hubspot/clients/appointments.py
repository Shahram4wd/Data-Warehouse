"""
HubSpot appointments API client
"""
import logging
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, AsyncGenerator
from .base import HubSpotBaseClient

logger = logging.getLogger(__name__)

class HubSpotAppointmentsClient(HubSpotBaseClient):
    """HubSpot API client for appointments (custom object 0-421)"""
    
    async def fetch_appointments(self, last_sync: Optional[datetime] = None,
                               limit: int = 100, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch appointments from HubSpot custom object 0-421 with pagination"""
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
        
        # Define appointment properties (comprehensive list including new fields)
        properties = [
            # Basic appointment info
            "appointment_id", "genius_appointment_id", "marketsharp_id",
            "hs_appointment_name", "hs_appointment_start", "hs_appointment_end",
            "hs_duration", "hs_object_id", "hs_createdate", "hs_lastmodifieddate",
            "hs_pipeline", "hs_pipeline_stage",
            
            # Contact information
            "first_name", "last_name", "email", "phone1", "phone2",
            "address1", "address2", "city", "state", "zip",
            
            # Appointment scheduling
            "date", "time", "duration", "appointment_status", "appointment_confirmed",
            "appointment_response", "is_complete",
            
            # Cancel reasons
            "cancel_reason", "div_cancel_reasons", "qc_cancel_reasons",
            
            # Services and interests
            "appointment_services", "lead_services", "product_interest_primary", "product_interest_secondary",
            
            # User and assignment info
            "user_id", "canvasser", "canvasser_id", "canvasser_email",
            "hubspot_owner_id", "hubspot_owner_assigneddate", "hubspot_team_id",
            
            # Division and organizational info
            "division_id", "division",
            
            # Source tracking
            "primary_source", "secondary_source", "prospect_id", "prospect_source_id",
            "hscontact_id", "sourcefield",
            
            # Appointment type and completion
            "type_id", "type_id_text", "marketsharp_appt_type",
            
            # Completion details
            "complete_date", "complete_outcome_id", "complete_outcome_id_text", "complete_user_id",
            
            # Confirmation details
            "confirm_date", "confirm_user_id", "confirm_with",
            
            # Assignment details
            "assign_date", "add_date", "add_user_id",
            
            # Arrivy integration fields
            "arrivy_appt_date", "arrivy_confirm_date", "arrivy_confirm_user", "arrivy_created_by",
            "arrivy_details", "arrivy_notes", "arrivy_object_id", "arrivy_result_full_string",
            "arrivy_salesrep_first_name", "arrivy_salesrep_last_name", "arrivy_status", "arrivy_status_title",
            "arrivy_user", "arrivy_user_divison_id", "arrivy_user_external_id", "arrivy_username",
            
            # SalesPro integration fields
            "salespro_both_homeowners", "salespro_consider_solar", "salespro_customer_id",
            "salespro_deadline", "salespro_deposit_type", "salespro_estimate_id",
            "salespro_fileurl_contract", "salespro_fileurl_estimate", "salespro_financing",
            "salespro_job_size", "salespro_job_type", "salespro_last_price_offered",
            "salespro_notes", "salespro_one_year_price", "salespro_preferred_payment",
            "salespro_requested_start", "salespro_result", "salespro_result_notes",
            "salespro_result_reason_demo", "salespro_result_reason_no_demo",
            
            # Additional fields
            "notes", "log", "title", "marketing_task_id", "leap_estimate_id",
            "spouses_present", "year_built", "error_details", "tester_test",
            
            # Additional missing fields
            "created_by_make", "f9_tfuid", "set_date",
            
            # Genius integration fields
            "genius_quote_id", "genius_quote_response", "genius_quote_response_status",
            "genius_response", "genius_response_status", "genius_resubmit"
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
