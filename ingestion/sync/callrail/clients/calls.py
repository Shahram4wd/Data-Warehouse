"""
CallRail calls client for fetching call data
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from .base import CallRailBaseClient

logger = logging.getLogger(__name__)


class CallsClient(CallRailBaseClient):
    """Client for CallRail calls API endpoint"""
    
    def get_date_filter_field(self) -> Optional[str]:
        """CallRail calls use 'start_time' for date filtering"""
        return 'start_time'
    
    def extract_data_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract calls data from CallRail API response"""
        return response.get('calls', [])
    
    async def fetch_calls(
        self, 
        account_id: str,
        since_date: Optional[datetime] = None,
        **params
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch calls from CallRail API with delta sync support
        
        Args:
            account_id: CallRail account ID
            since_date: Only fetch calls since this date (for delta sync)
            **params: Additional query parameters
        """
        endpoint = f'a/{account_id}/calls.json'
        
        # Default parameters for calls
        default_params = {
            'per_page': 100,
            'fields': 'id,answered,business_phone_number,customer_city,customer_country,'
                     'customer_name,customer_phone_number,customer_state,direction,duration,'
                     'recording,recording_duration,recording_player,start_time,'
                     'tracking_phone_number,voicemail,agent_email,call_type,campaign,'
                     'company_id,company_name,note,tags,lead_status,value'
        }
        
        # Merge with provided parameters
        call_params = {**default_params, **params}
        
        logger.info(f"Fetching CallRail calls for account {account_id}")
        if since_date:
            logger.info(f"Delta sync since: {since_date}")
        
        async for batch in self.fetch_paginated_data(endpoint, since_date, **call_params):
            yield batch
    
    async def get_call_by_id(self, account_id: str, call_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific call by ID"""
        endpoint = f'a/{account_id}/calls/{call_id}.json'
        
        try:
            response = await self.make_request('GET', endpoint)
            return response
        except Exception as e:
            logger.error(f"Failed to fetch call {call_id}: {e}")
            return None
    
    async def get_call_summary(
        self, 
        account_id: str, 
        date_range: str = "recent"
    ) -> Dict[str, Any]:
        """Get call summary statistics"""
        endpoint = f'a/{account_id}/calls/summary.json'
        
        params = {'date_range': date_range}
        
        try:
            response = await self.make_request('GET', endpoint, params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to fetch call summary: {e}")
            return {}
    
    async def search_calls(
        self, 
        account_id: str,
        search_params: Dict[str, Any]
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Search calls with advanced filters
        
        Args:
            account_id: CallRail account ID
            search_params: Search parameters like phone numbers, tags, etc.
        """
        endpoint = f'a/{account_id}/calls.json'
        
        logger.info(f"Searching CallRail calls with params: {search_params}")
        
        async for batch in self.fetch_paginated_data(endpoint, **search_params):
            yield batch
