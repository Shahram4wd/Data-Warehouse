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
        
        # Define appointment properties (essential ones for performance)
        properties = [
            "appointment_id", "genius_appointment_id", "marketsharp_id",
            "hs_appointment_name", "hs_appointment_start", "hs_appointment_end",
            "hs_duration", "hs_object_id", "hs_createdate", "hs_lastmodifieddate",
            "first_name", "last_name", "email", "phone1", "address1", "city", "state", "zip",
            "date", "time", "duration", "appointment_status", "is_complete",
            "user_id", "division_id", "hubspot_owner_id"
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
