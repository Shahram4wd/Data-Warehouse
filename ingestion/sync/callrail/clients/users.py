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
        since_date: Optional[datetime] = None,
        **params
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch users from CallRail API
        
        Args:
            since_date: Optional datetime for delta sync
            **params: Additional query parameters
            
        Yields:
            List[Dict]: Batches of user records
        """
        # First fetch all accounts
        accounts_response = await self.make_request('GET', 'a.json')
        accounts = accounts_response.get('accounts', [])
        
        # Default parameters for users
        default_params = {
            'per_page': 100,
        }
        
        # Merge with provided parameters
        user_params = {**default_params, **params}
        
        # Iterate through each account
        for account in accounts:
            account_id = account.get('id')
            if not account_id:
                continue
                
            endpoint = f'a/{account_id}/users.json'
            
            logger.info(f"Fetching CallRail users for account {account_id}")
            if since_date:
                logger.info(f"Delta sync since: {since_date}")
            
            async for batch in self.fetch_paginated_data(endpoint, since_date, **user_params):
                yield batch
