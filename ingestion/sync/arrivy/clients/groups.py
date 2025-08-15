"""
Arrivy Groups API Client

Handles group-specific operations for Arrivy API.
Groups represent organizational units, teams, or divisions.
"""

from typing import Dict, List, Optional, AsyncGenerator, Any
from datetime import datetime
import logging

from .base import ArrivyBaseClient

logger = logging.getLogger(__name__)

class ArrivyGroupsClient(ArrivyBaseClient):
    """Client for Arrivy groups/divisions API operations"""
    
    async def fetch_groups(self, last_sync: Optional[datetime] = None,
                          page_size: int = 100, max_records: Optional[int] = None) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch groups from Arrivy API with delta sync support
        
        Args:
            last_sync: Last sync timestamp for delta sync
            page_size: Records per page
            max_records: Maximum records to fetch (optional)
            
        Yields:
            Batches of group records
        """
        logger.info(f"Fetching groups with page_size={page_size}, last_sync={last_sync}")
        
        records_fetched = 0
        
        async for batch in self.fetch_paginated_data(
            endpoint="groups",
            last_sync=last_sync,
            page_size=page_size
        ):
            # Check max_records limit
            if max_records and records_fetched >= max_records:
                logger.info(f"Reached max_records limit of {max_records}")
                break
            
            # Trim batch if it would exceed max_records
            if max_records and records_fetched + len(batch) > max_records:
                remaining = max_records - records_fetched
                batch = batch[:remaining]
            
            records_fetched += len(batch)
            logger.debug(f"Fetched batch of {len(batch)} groups (total: {records_fetched})")
            yield batch
    
    async def fetch_crews(self, last_sync: Optional[datetime] = None,
                         page_size: int = 100, max_records: Optional[int] = None) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch crews (divisions) from Arrivy API
        
        Crews and groups might be different endpoints representing similar concepts.
        This method fetches from the crews endpoint.
        
        Args:
            last_sync: Last sync timestamp for delta sync
            page_size: Records per page
            max_records: Maximum records to fetch (optional)
            
        Yields:
            Batches of crew/division records
        """
        logger.info(f"Fetching crews with page_size={page_size}, last_sync={last_sync}")
        
        records_fetched = 0
        
        async for batch in self.fetch_paginated_data(
            endpoint="crews",
            last_sync=last_sync,
            page_size=page_size
        ):
            # Check max_records limit
            if max_records and records_fetched >= max_records:
                logger.info(f"Reached max_records limit of {max_records}")
                break
            
            # Trim batch if it would exceed max_records
            if max_records and records_fetched + len(batch) > max_records:
                remaining = max_records - records_fetched
                batch = batch[:remaining]
            
            records_fetched += len(batch)
            logger.debug(f"Fetched batch of {len(batch)} crews (total: {records_fetched})")
            yield batch
    
    async def fetch_crew_singular(self, last_sync: Optional[datetime] = None,
                                 page_size: int = 100, max_records: Optional[int] = None) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch from singular crew endpoint to test API differences
        
        Args:
            last_sync: Last sync timestamp for delta sync
            page_size: Records per page
            max_records: Maximum records to fetch (optional)
            
        Yields:
            Batches of crew records
        """
        logger.info(f"Fetching crew (singular) with page_size={page_size}, last_sync={last_sync}")
        
        records_fetched = 0
        
        async for batch in self.fetch_paginated_data(
            endpoint="crew",  # singular endpoint
            last_sync=last_sync,
            page_size=page_size
        ):
            # Check max_records limit
            if max_records and records_fetched >= max_records:
                logger.info(f"Reached max_records limit of {max_records}")
                break
            
            # Trim batch if it would exceed max_records
            if max_records and records_fetched + len(batch) > max_records:
                remaining = max_records - records_fetched
                batch = batch[:remaining]
            
            records_fetched += len(batch)
            logger.debug(f"Fetched batch of {len(batch)} crew records (singular) (total: {records_fetched})")
            yield batch
    
    async def fetch_group_by_id(self, group_id: str) -> Dict[str, Any]:
        """
        Fetch a specific group by ID
        
        Args:
            group_id: Group ID to fetch
            
        Returns:
            Group data
        """
        logger.debug(f"Fetching group by ID: {group_id}")
        
        result = await self._make_request(f"groups/{group_id}")
        return result.get('data', {})
    
    async def get_groups_count(self) -> int:
        """
        Get total count of groups without fetching all data
        
        Returns:
            Total group count
        """
        result = await self._make_request("groups", {"page_size": 1, "page": 1})
        pagination = result.get('pagination')
        if pagination:
            return pagination.get('total_count', 0)
        return len(result.get('data', []))
    
    async def fetch_location_reports(self) -> List[Dict[str, Any]]:
        """
        Fetch location reports from Arrivy API
        
        Location reports provide GPS tracking data for entities.
        
        Returns:
            List of location reports
        """
        logger.info("Fetching location reports")
        
        # Based on Arrivy documentation: GET /entities returns last report for all entities
        possible_endpoints = [
            "entities",  # Primary endpoint for location reports
            "entities/readings",  # Alternative bulk readings endpoint
        ]
        
        for endpoint in possible_endpoints:
            try:
                result = await self._make_request(endpoint)
                data = result.get('data', [])
                if data:
                    logger.debug(f"Found location reports using endpoint: {endpoint}")
                    return data
            except Exception as e:
                logger.debug(f"Location reports endpoint {endpoint} failed: {str(e)}")
                continue
        
        # Location reports might not be available for this configuration
        logger.info("Location reports endpoint not available in this Arrivy API configuration")
        return []
