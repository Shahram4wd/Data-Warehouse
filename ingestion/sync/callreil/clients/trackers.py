"""
CallReil trackers client for fetching tracker data
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from .base import CallReilBaseClient

logger = logging.getLogger(__name__)


class TrackersClient(CallReilBaseClient):
    """Client for CallReil trackers API endpoint"""
    
    def get_date_filter_field(self) -> Optional[str]:
        """CallRail trackers use 'created_at' for date filtering"""
        return 'created_at'
    
    def extract_data_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract trackers data from CallRail API response"""
        return response.get('trackers', [])
    
    async def fetch_trackers(
        self, 
        account_id: str,
        company_id: Optional[str] = None,
        since_date: Optional[datetime] = None,
        **params
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch trackers from CallRail API
        
        Args:
            account_id: CallRail account ID
            company_id: Optional company ID to filter trackers
            since_date: Only fetch trackers since this date (for delta sync)
            **params: Additional query parameters
        """
        if company_id:
            endpoint = f'a/{account_id}/companies/{company_id}/trackers.json'
        else:
            endpoint = f'a/{account_id}/trackers.json'
        
        # Default parameters for trackers
        default_params = {
            'per_page': 100,
        }
        
        # Merge with provided parameters
        tracker_params = {**default_params, **params}
        
        logger.info(f"Fetching CallRail trackers for account {account_id}")
        if company_id:
            logger.info(f"Filtering by company: {company_id}")
        if since_date:
            logger.info(f"Delta sync since: {since_date}")
        
        async for batch in self.fetch_paginated_data(endpoint, since_date, **tracker_params):
            yield batch
    
    async def get_tracker_by_id(
        self, 
        account_id: str, 
        tracker_id: str,
        company_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a specific tracker by ID"""
        if company_id:
            endpoint = f'a/{account_id}/companies/{company_id}/trackers/{tracker_id}.json'
        else:
            endpoint = f'a/{account_id}/trackers/{tracker_id}.json'
        
        try:
            response = await self.make_request('GET', endpoint)
            return response
        except Exception as e:
            logger.error(f"Failed to fetch tracker {tracker_id}: {e}")
            return None
