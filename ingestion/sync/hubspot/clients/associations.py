"""
HubSpot associations API client
"""
import logging
from typing import List, Dict, Any
from .base import HubSpotBaseClient

logger = logging.getLogger(__name__)

class HubSpotAssociationsClient(HubSpotBaseClient):
    """HubSpot API client for associations between objects"""
    
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
