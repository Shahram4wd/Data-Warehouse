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
        account_id: str,
        since_date: Optional[datetime] = None,
        **params
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch text messages from CallRail API
        
        Args:
            account_id: CallRail account ID
            since_date: Optional datetime for delta sync
            **params: Additional query parameters
            
        Yields:
            List[Dict]: Batches of text message records
        """
        logger.info(f"Fetching text messages for account {account_id}")
        
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
                endpoint=f"/accounts/{account_id}/text_messages.json",
                params=query_params,
                **params
            ):
                if batch:
                    logger.debug(f"Fetched {len(batch)} text messages")
                    yield batch
                else:
                    logger.info("No more text messages to fetch")
                    break
                    
        except Exception as e:
            logger.error(f"Error fetching text messages: {e}")
            raise
