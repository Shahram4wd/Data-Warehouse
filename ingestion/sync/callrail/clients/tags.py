"""
CallRail tags client for fetching tag data
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from .base import CallRailBaseClient

logger = logging.getLogger(__name__)


class TagsClient(CallRailBaseClient):
    """Client for CallRail tags API endpoint"""
    
    def get_date_filter_field(self) -> Optional[str]:
        """CallRail tags use 'created_at' for date filtering"""
        return 'created_at'
    
    def extract_data_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tags data from CallRail API response"""
        return response.get('tags', [])
    
    async def fetch_tags(
        self, 
        since_date: Optional[datetime] = None,
        **params
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch tags from CallRail API
        
        Args:
            since_date: Optional datetime for delta sync
            **params: Additional query parameters
            
        Yields:
            List[Dict]: Batches of tag records
        """
        # First fetch all accounts
        accounts_response = await self.make_request('GET', 'a.json')
        accounts = accounts_response.get('accounts', [])
        
        # Default parameters for tags
        default_params = {
            'per_page': 100,
        }
        
        # Merge with provided parameters
        tag_params = {**default_params, **params}
        
        # Iterate through each account
        for account in accounts:
            account_id = account.get('id')
            if not account_id:
                continue
                
            endpoint = f'a/{account_id}/tags.json'
            
            logger.info(f"Fetching CallRail tags for account {account_id}")
            if since_date:
                logger.info(f"Delta sync since: {since_date}")
            
            async for batch in self.fetch_paginated_data(endpoint, since_date, **tag_params):
                yield batch
