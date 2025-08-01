"""
CallRail text messages client for fetching text message data
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from .base import CallRailBaseClient

logger = logging.getLogger(__name__)


class TextMessagesClient(CallRailBaseClient):
    """Client for CallRail text messages API endpoint"""
    
    def get_date_filter_field(self) -> Optional[str]:
        """CallRail text messages use 'sent_at' for date filtering"""
        return 'sent_at'
    
    def extract_data_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract text messages data from CallRail API response"""
        return response.get('text_messages', [])
    
    async def fetch_text_messages(
        self, 
        since_date: Optional[datetime] = None,
        **params
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch text messages from CallRail API
        
        Args:
            since_date: Optional datetime for delta sync
            **params: Additional query parameters
            
        Yields:
            List[Dict]: Batches of text message records
        """
        # First fetch all accounts
        accounts_response = await self.make_request('GET', 'a.json')
        accounts = accounts_response.get('accounts', [])
        
        # Default parameters for text messages
        default_params = {
            'per_page': 100,
        }
        
        # Merge with provided parameters
        message_params = {**default_params, **params}
        
        # Iterate through each account
        for account in accounts:
            account_id = account.get('id')
            if not account_id:
                continue
                
            endpoint = f'a/{account_id}/text_messages.json'
            
            logger.info(f"Fetching CallRail text messages for account {account_id}")
            if since_date:
                logger.info(f"Delta sync since: {since_date}")
            
            async for batch in self.fetch_paginated_data(endpoint, since_date, **message_params):
                yield batch
