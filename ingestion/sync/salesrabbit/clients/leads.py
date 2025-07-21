"""
SalesRabbit leads API client with incremental sync capabilities
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, AsyncGenerator
from .base import SalesRabbitBaseClient
from ingestion.base.exceptions import DataSourceException

logger = logging.getLogger(__name__)

class SalesRabbitLeadsClient(SalesRabbitBaseClient):
    """Lead-specific client with incremental sync capabilities"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.endpoints = {
            'leads': '/leads',  # Updated to match working original client
            'leads_search': '/leads/search',
            'leads_count': '/leads/count'
        }
    
    async def fetch_all_leads(self, limit: int = 1000, max_records: int = 0) -> List[Dict[str, Any]]:
        """Fetch all leads with pagination support"""
        try:
            logger.info("Fetching all SalesRabbit leads")
            params = {'limit': limit}
            
            # If max_records is specified, use modified pagination
            if max_records > 0:
                return await self._make_limited_paginated_request(
                    self.endpoints['leads'], params, max_records
                )
            else:
                return await self._make_paginated_request(self.endpoints['leads'], params)
        except Exception as e:
            logger.error(f"Error fetching all leads: {e}")
            # Return empty list instead of raising exception for graceful handling
            logger.warning("Returning empty list due to API error - sync will continue with 0 records")
            return []
    
    async def fetch_leads_since(self, since_date: datetime, limit: int = 1000, max_records: int = 0) -> List[Dict[str, Any]]:
        """Fetch leads modified since specific date - FRAMEWORK STANDARD"""
        try:
            params = {
                'modified_since': since_date.isoformat(),
                'sort': 'date_modified',
                'order': 'asc',
                'limit': limit
            }
            
            logger.info(f"Fetching SalesRabbit leads modified since {since_date}")
            
            # If max_records is specified, use modified pagination
            if max_records > 0:
                return await self._make_limited_paginated_request(
                    self.endpoints['leads'], params, max_records
                )
            else:
                return await self._make_paginated_request(self.endpoints['leads'], params)
        except Exception as e:
            logger.error(f"Error fetching leads since {since_date}: {e}")
            # Return empty list instead of raising exception for graceful handling
            logger.warning("Returning empty list due to API error - sync will continue with 0 records")
            return []
    
    async def get_lead_count_since(self, since_date: Optional[datetime] = None) -> int:
        """Get count of leads for sync planning"""
        try:
            params = {}
            if since_date:
                params['modified_since'] = since_date.isoformat()
            
            # Use context manager for proper session handling
            async with self as client:
                response = await client.make_request('GET', self.endpoints['leads_count'], params=params)
            
            # Handle different response formats
            if isinstance(response, dict):
                count = response.get('count', response.get('total', 0))
            else:
                count = 0
            
            logger.info(f"Lead count: {count}")
            return count
        except Exception as e:
            logger.warning(f"Could not get lead count: {e}")
            return 0
    
    async def get_lead_by_id(self, lead_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific lead by ID"""
        try:
            endpoint = f"{self.endpoints['leads']}/{lead_id}"
            async with self as client:
                response = await client.make_request('GET', endpoint)
            
            if isinstance(response, dict):
                return response
            return None
        except Exception as e:
            logger.error(f"Error fetching lead {lead_id}: {e}")
            return None
    
    async def search_leads(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search leads with specific criteria"""
        try:
            logger.info(f"Searching SalesRabbit leads with params: {search_params}")
            return await self._make_paginated_request(self.endpoints['leads_search'], search_params)
        except Exception as e:
            logger.error(f"Error searching leads: {e}")
            raise DataSourceException(f"Failed to search leads: {e}")
    
    async def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            await self.authenticate()
            # Try to get a small number of leads to test connection
            await self.get_lead_count_since()
            logger.info("SalesRabbit API connection test successful")
            return True
        except Exception as e:
            logger.error(f"SalesRabbit API connection test failed: {e}")
            return False
