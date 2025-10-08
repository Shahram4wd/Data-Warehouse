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
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_endpoint = "crm/v3/objects/0-1"  # Custom object endpoint for contacts
    
    def _get_contact_properties(self) -> List[str]:
        """Get contact properties that match the HubSpot Contact model fields"""
        return [
            # Core fields
            "id",
            "address",
            "adgroupid",
            "ap_leadid",
            "campaign_content",
            "campaign_name",
            "city",
            "clickcheck",
            "clicktype",
            "comments",
            "createdate",
            "division",
            "email",
            "firstname",
            "hs_google_click_id",
            "hs_object_id",
            "lastmodifieddate",
            "lastname",
            "lead_salesrabbit_lead_id",
            "marketsharp_id",
            "msm_source",
            "original_lead_source",
            "original_lead_source_created",
            "phone",
            "price",
            "reference_code",
            "search_terms",
            "state",
            "tier",
            "trustedform_cert_url",
            "vendorleadid",
            "vertical",
            "zip",
            
            # Lead-related fields
            "lead_added_by",
            "lead_added_by_latitude",
            "lead_added_by_longitude",
            "lead_added_by_supervisor",
            "lead_address1",
            "lead_agent_id",
            "lead_agent_name",
            "lead_call_screen_viewed_by",
            "lead_call_screen_viewed_on",
            "lead_cdyne_county",
            "lead_city",
            "lead_contact",
            "lead_copied_from_id",
            "lead_copied_from_on",
            "lead_cost",
            "lead_cwp_client",
            "lead_dead_by",
            "lead_dead_on",
            "lead_division",
            "lead_do_not_call_before",
            "lead_estimate_confirmed_by",
            "lead_estimate_confirmed_on",
            "lead_express_consent_set_by",
            "lead_express_consent_set_on",
            "lead_express_consent_source",
            "lead_express_consent_upload_file_id",
            "lead_id",
            "lead_import_source",
            "lead_invalid_address",
            "lead_is_carpentry_followup",
            "lead_is_dnc",
            "lead_is_dummy",
            "lead_is_estimate_confirmed",
            "lead_is_estimate_set",
            "lead_is_express_consent",
            "lead_is_express_consent_being_reviewed",
            "lead_is_high_potential",
            "lead_is_mobile_lead",
            "lead_is_valid_address",
            "lead_is_valid_email",
            "lead_is_year_built_verified",
            "lead_is_zillow",
            "lead_job_type",
            "lead_notes",
            "lead_phone1",
            "lead_phone2",
            "lead_phone3",
            "lead_prospect_id",
            "lead_rating",
            "lead_salesrabbit_lead_id_new",
            "lead_source",
            "lead_source_notes",
            "lead_sourced_on",
            "lead_state",
            "lead_status",
            "lead_substatus",
            "lead_type1",
            "lead_type2",
            "lead_type4",
            "lead_viewed_on",
            "lead_with_dm",
            "lead_year_built",
            "lead_zip",
            
            # Source fields
            "hge_primary_source",
            "hge_secondary_source"
        ]
    
    async def fetch_contacts(self, last_sync: Optional[datetime] = None, 
                           limit: int = 100, appointment_id: Optional[int] = None,
                           contact_id: Optional[str] = None, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch contacts from HubSpot API with pagination and filtering support"""
        
        # If specific appointment_id or contact_id is provided, fetch single contact
        if appointment_id or contact_id:
            contact = await self._fetch_single_contact(appointment_id, contact_id)
            if contact:
                yield [contact]
            return
        
        # Otherwise, fetch paginated contacts
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
    
    async def _fetch_single_contact(self, appointment_id: Optional[int] = None, 
                                   contact_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch a single contact by appointment ID or contact ID"""
        properties = self._get_contact_properties()
        
        try:
            if contact_id:
                # Fetch by contact ID
                endpoint = f"{self.base_endpoint}/{contact_id}"
                params = {
                    "properties": ",".join(properties)
                }
                
                response_data = await self.make_request("GET", endpoint, params=params)
                return response_data
            
            elif appointment_id:
                # Search for contact by appointment ID
                endpoint = f"{self.base_endpoint}/search"
                payload = {
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "appointment_id",
                            "operator": "EQ",
                            "value": str(appointment_id)
                        }]
                    }],
                    "properties": properties,
                    "limit": 1
                }
                
                response_data = await self.make_request("POST", endpoint, json=payload)
                results = response_data.get("results", [])
                return results[0] if results else None
                
        except Exception as e:
            logger.error(f"Error fetching single contact (appointment_id={appointment_id}, contact_id={contact_id}): {e}")
            return None
    
    async def _fetch_contacts_page(self, last_sync: Optional[datetime] = None,
                                 page_token: Optional[str] = None,
                                 limit: int = 100) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch a single page of contacts"""
        
        # Define properties to retrieve
        properties = self._get_contact_properties()
        
        try:
            # Always use the regular endpoint to avoid the 10,000 result limit
            # Filter by lastmodifieddate locally for incremental syncs
            endpoint = self.base_endpoint
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
            
            # Filter results locally if last_sync is provided (incremental sync)
            if last_sync and results:
                filtered_results = []
                for contact in results:
                    # Parse the lastmodifieddate from the contact
                    props = contact.get("properties", {})
                    lastmodified_str = props.get("lastmodifieddate")
                    
                    if lastmodified_str:
                        try:
                            # HubSpot can return timestamps in different formats:
                            # 1. ISO format: "2025-10-08T04:00:42.602Z"
                            # 2. Milliseconds since epoch: "1728361242602"
                            
                            if 'T' in lastmodified_str and 'Z' in lastmodified_str:
                                # ISO format - parse as datetime
                                from datetime import datetime
                                # Remove microseconds if present and parse
                                if '.' in lastmodified_str:
                                    # Handle microseconds: 2025-10-08T04:00:42.602Z
                                    dt_part, _ = lastmodified_str.split('.')
                                    tz_part = 'Z'
                                    clean_str = f"{dt_part}Z"
                                else:
                                    clean_str = lastmodified_str
                                
                                lastmodified_dt = datetime.fromisoformat(clean_str.replace('Z', '+00:00'))
                                # Convert to naive datetime for comparison (remove timezone info)
                                lastmodified_dt = lastmodified_dt.replace(tzinfo=None)
                            else:
                                # Timestamp format - convert from milliseconds
                                lastmodified_timestamp = int(lastmodified_str)
                                lastmodified_dt = datetime.fromtimestamp(lastmodified_timestamp / 1000)
                            
                            # Include contacts modified since last_sync
                            # Ensure both datetimes are naive for comparison
                            last_sync_naive = last_sync.replace(tzinfo=None) if last_sync.tzinfo else last_sync
                            if lastmodified_dt >= last_sync_naive:
                                filtered_results.append(contact)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Failed to parse lastmodifieddate '{lastmodified_str}' for contact {contact.get('id')}: {e}")
                            # Include the contact if we can't parse the date to be safe
                            filtered_results.append(contact)
                    else:
                        # Include contacts without lastmodifieddate to be safe
                        filtered_results.append(contact)
                
                logger.info(f"Fetched {len(results)} contacts from HubSpot, {len(filtered_results)} modified since {last_sync}")
                return filtered_results, next_page
            
            logger.info(f"Fetched {len(results)} contacts from HubSpot")
            return results, next_page
            
        except Exception as e:
            logger.error(f"Error fetching contacts page: {e}")
            return [], None
