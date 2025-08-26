"""
SalesRabbit users API client with incremental sync capabilities
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, AsyncGenerator
from django.utils.dateparse import parse_datetime
from .base import SalesRabbitBaseClient
from ingestion.base.exceptions import DataSourceException

logger = logging.getLogger(__name__)

class SalesRabbitUsersClient(SalesRabbitBaseClient):
    """User-specific client with incremental sync capabilities"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.endpoints = {
            'users': '/users',  # Main users endpoint
            'users_search': '/users/search'  # Search endpoint if needed
        }
    
    async def fetch_all_users(self, limit: int = 1000, max_records: int = 0) -> List[Dict[str, Any]]:
        """Fetch all users with pagination support"""
        try:
            logger.info("Fetching all SalesRabbit users")
            params = {'limit': limit}
            
            # If max_records is specified, use modified pagination
            if max_records > 0:
                return await self._make_limited_paginated_request(
                    self.endpoints['users'], params, max_records
                )
            else:
                return await self._make_paginated_request(self.endpoints['users'], params)
        except Exception as e:
            logger.error(f"Error fetching all users: {e}")
            # Return empty list instead of raising exception for graceful handling
            logger.warning("Returning empty list due to API error - sync will continue with 0 records")
            return []
    
    async def fetch_users_since(self, since_date: datetime, limit: int = 1000, max_records: int = 0) -> List[Dict[str, Any]]:
        """Fetch users modified since specific date - SERVER-SIDE FILTERING using If-Modified-Since header"""
        try:
            # SalesRabbit API supports If-Modified-Since header for server-side filtering
            logger.info(f"Fetching SalesRabbit users modified since {since_date} using If-Modified-Since header")
            
            # Format the date for SalesRabbit API (requires +00:00 timezone offset as per docs)
            date_param = since_date.strftime('%Y-%m-%dT%H:%M:%S+00:00')
            
            # Use If-Modified-Since header instead of query parameter
            extra_headers = {'If-Modified-Since': date_param}
            params = {'limit': limit}
            
            logger.info(f"Using If-Modified-Since header: {date_param}")
            
            # If max_records is specified, use modified pagination
            if max_records > 0:
                return await self._make_limited_paginated_request_with_headers(
                    self.endpoints['users'], params, max_records, extra_headers
                )
            else:
                return await self._make_paginated_request_with_headers(self.endpoints['users'], params, extra_headers)
            
        except Exception as e:
            logger.error(f"Error fetching users since {since_date}: {e}")
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
                    return response.get('data', response.get('users', []))
                else:
                    return []
            except Exception as e:
                logger.error(f"Error in single page request: {e}")
                return []
    
    async def get_user_count_since(self, since_date: Optional[datetime] = None) -> int:
        """Get count of users for sync planning"""
        try:
            # SalesRabbit API doesn't have a dedicated count endpoint
            # Instead, we'll fetch the first page and use the response metadata if available
            # or return 0 to skip count-based planning
            params = {'limit': 1, 'page': 1}
            if since_date:
                # Use If-Modified-Since header for consistency with fetch_users_since
                date_param = since_date.strftime('%Y-%m-%dT%H:%M:%S+00:00')
                extra_headers = {'If-Modified-Since': date_param}
                
                async with self as client:
                    response = await client.make_request('GET', self.endpoints['users'], params=params, headers=extra_headers)
                    
                    if isinstance(response, dict) and 'meta' in response:
                        # If pagination metadata is available, use it
                        meta = response.get('meta', {})
                        total = meta.get('total', 0)
                        if total > 0:
                            return total
            
            # Fallback: return 0 to skip count-based planning
            return 0
            
        except Exception as e:
            logger.warning(f"Could not get user count: {e}")
            return 0
    
    async def validate_connection(self) -> bool:
        """Test API connection by fetching a single user"""
        try:
            logger.info("Testing SalesRabbit Users API connection...")
            
            async with self as client:
                response = await client.make_request('GET', self.endpoints['users'], params={'limit': 1})
                
                if isinstance(response, dict) and 'data' in response:
                    user_count = len(response.get('data', []))
                    logger.info(f"✓ SalesRabbit Users API connection successful - retrieved {user_count} user(s)")
                    return True
                elif isinstance(response, list) and len(response) >= 0:
                    logger.info(f"✓ SalesRabbit Users API connection successful - retrieved {len(response)} user(s)")
                    return True
                else:
                    logger.error("✗ Unexpected response format from SalesRabbit Users API")
                    return False
                    
        except Exception as e:
            logger.error(f"✗ SalesRabbit Users API connection failed: {e}")
            return False
