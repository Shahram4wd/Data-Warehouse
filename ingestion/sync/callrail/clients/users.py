"""
CallRail users client for fetching user data
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from .base import CallRailBaseClient

logger = logging.getLogger(__name__)


class UsersClient(CallRailBaseClient):
    """Client for CallRail users API endpoint"""
    
    def get_date_filter_field(self) -> Optional[str]:
        """CallRail users use 'created_at' for date filtering"""
        return 'created_at'
    
    def extract_data_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract users data from CallRail API response"""
        return response.get('users', [])
    
    async def fetch_users(
        self, 
        account_id: str,
        since_date: Optional[datetime] = None,
        **params
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch users from CallRail API
        
        Args:
            account_id: CallRail account ID
            since_date: Optional datetime for delta sync
            **params: Additional query parameters
            
        Yields:
            List[Dict]: Batches of user records
        """
        logger.info(f"Fetching users for account {account_id}")
        
        # Build query parameters
        query_params = {
            'page': 1,
            'per_page': params.get('batch_size', 100),
        }
        
        # Add date filter if provided
        if since_date:
            date_field = self.get_date_filter_field()
            if date_field:
                query_params[f'filters[{date_field}]'] = since_date.isoformat()
        
        # Add any additional filters
        query_params.update(params.get('filters', {}))
        
        try:
            async for batch in self.fetch_paginated_data(
                endpoint=f"/accounts/{account_id}/users.json",
                params=query_params,
                **params
            ):
                if batch:
                    logger.debug(f"Fetched {len(batch)} users")
                    yield batch
                else:
                    logger.info("No more users to fetch")
                    break
                    
        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            raise
