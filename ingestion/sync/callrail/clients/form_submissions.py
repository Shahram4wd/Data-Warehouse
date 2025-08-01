"""
CallRail form submissions client for fetching form submission data
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from .base import CallRailBaseClient

logger = logging.getLogger(__name__)


class FormSubmissionsClient(CallRailBaseClient):
    """Client for CallRail form submissions API endpoint"""
    
    def get_date_filter_field(self) -> Optional[str]:
        """CallRail form submissions use 'submission_time' for date filtering"""
        return 'submission_time'
    
    def extract_data_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract form submissions data from CallRail API response"""
        return response.get('form_submissions', [])
    
    async def fetch_form_submissions(
        self, 
        since_date: Optional[datetime] = None,
        **params
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch form submissions from CallRail API
        
        Args:
            since_date: Optional datetime for delta sync
            **params: Additional query parameters
            
        Yields:
            List[Dict]: Batches of form submission records
        """
        # First fetch all accounts
        accounts_response = await self.make_request('GET', 'a.json')
        accounts = accounts_response.get('accounts', [])
        
        # Default parameters for form submissions
        default_params = {
            'per_page': 100,
        }
        
        # Merge with provided parameters
        submission_params = {**default_params, **params}
        
        # Iterate through each account
        for account in accounts:
            account_id = account.get('id')
            if not account_id:
                continue
                
            endpoint = f'a/{account_id}/form_submissions.json'
            
            logger.info(f"Fetching CallRail form submissions for account {account_id}")
            if since_date:
                logger.info(f"Delta sync since: {since_date}")
            
            async for batch in self.fetch_paginated_data(endpoint, since_date, **submission_params):
                yield batch
