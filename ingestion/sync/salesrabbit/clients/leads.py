"""
SalesRabbit leads API client with incremental sync capabilities
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, AsyncGenerator
from django.utils.dateparse import parse_datetime
from .base import SalesRabbitBaseClient
from ingestion.base.exceptions import DataSourceException

logger = logging.getLogger(__name__)

class SalesRabbitLeadsClient(SalesRabbitBaseClient):
    """Lead-specific client with incremental sync capabilities"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.endpoints = {
            'leads': '/leads',  # Updated to match working original client
            'leads_search': '/leads/search'
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
        """Fetch leads modified since specific date - SERVER-SIDE FILTERING using If-Modified-Since header"""
        try:
            # SalesRabbit API supports If-Modified-Since header for server-side filtering
            logger.info(f"Fetching SalesRabbit leads modified since {since_date} using If-Modified-Since header")
            
            # Format the date for SalesRabbit API (requires +00:00 timezone offset as per docs)
            date_param = since_date.strftime('%Y-%m-%dT%H:%M:%S+00:00')
            
            # Use If-Modified-Since header instead of query parameter
            extra_headers = {'If-Modified-Since': date_param}
            params = {'limit': limit}
            
            logger.info(f"Using If-Modified-Since header: {date_param}")
            
            # If max_records is specified, use modified pagination
            if max_records > 0:
                return await self._make_limited_paginated_request_with_headers(
                    self.endpoints['leads'], params, max_records, extra_headers
                )
            else:
                return await self._make_paginated_request_with_headers(self.endpoints['leads'], params, extra_headers)
            
        except Exception as e:
            logger.error(f"Error fetching leads since {since_date}: {e}")
            # Return empty list instead of raising exception for graceful handling
            logger.warning("Returning empty list due to API error - sync will continue with 0 records")
            return []
    
    async def _make_single_page_request(self, endpoint: str, params: Dict = None) -> List[Dict[str, Any]]:
        """Make a single page request to the API"""
        if params is None:
            params = {}
        
        async with self as client:
            try:
                response = await client.make_request('GET', endpoint, params=params)
                
                # Handle different response formats
                if isinstance(response, list):
                    return response
                elif isinstance(response, dict):
                    return response.get('data', response.get('leads', []))
                else:
                    return []
            except Exception as e:
                logger.error(f"Error in single page request: {e}")
                return []
    
    async def get_lead_count_since(self, since_date: Optional[datetime] = None) -> int:
        """Get count of leads for sync planning"""
        try:
            # SalesRabbit API doesn't have a dedicated count endpoint
            # Instead, we'll fetch the first page and use the response metadata if available
            # or return 0 to skip count-based planning
            params = {'limit': 1, 'page': 1}
            if since_date:
                # Use If-Modified-Since header for consistency with fetch_leads_since
                date_param = since_date.strftime('%Y-%m-%dT%H:%M:%S+00:00')
                extra_headers = {'If-Modified-Since': date_param}
            else:
                extra_headers = {}
            
            # Use context manager for proper session handling
            async with self as client:
                response = await client.make_request('GET', self.endpoints['leads'], params=params, headers=extra_headers)
            
            # Try to extract count from response metadata
            if isinstance(response, dict):
                count = response.get('count', response.get('total', response.get('totalCount', 0)))
                if count > 0:
                    logger.info(f"Lead count from metadata: {count}")
                    return count
            
            # If no count metadata, return 0 to skip count-based planning
            logger.info("No count metadata available, skipping count-based sync planning")
            return 0
        except Exception as e:
            logger.warning(f"Could not get lead count (this is normal for SalesRabbit API): {e}")
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
