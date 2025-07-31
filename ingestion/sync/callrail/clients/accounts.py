"""
CallRail accounts client for fetching account data
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from .base import CallRailBaseClient

logger = logging.getLogger(__name__)


class AccountsClient(CallRailBaseClient):
    """Client for CallRail accounts API endpoint"""
    
    def get_date_filter_field(self) -> Optional[str]:
        """CallRail accounts use 'created_at' for date filtering"""
        return 'created_at'
    
    def extract_data_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract accounts data from CallRail API response"""
        return response.get('accounts', [])
    
    async def fetch_accounts(
        self,
        since_date: Optional[datetime] = None,
        **params
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch accounts from CallRail API (reference: callrail_reference)
        """
        logger.info("Fetching accounts from CallRail API (using a.json endpoint)")

        # Build query parameters - only include valid API parameters
        query_params = {}
        
        # Add pagination parameters
        if 'per_page' in params:
            query_params['per_page'] = params['per_page']
        
        # Add date filter if provided
        if since_date:
            date_field = self.get_date_filter_field()
            if date_field:
                query_params[f'filters[{date_field}]'] = since_date.isoformat()

        try:
            # Make direct API call like reference implementation
            response = await self.make_request('GET', 'a.json', params=query_params)
            
            # Extract accounts data from response
            accounts = self.extract_data_from_response(response)
            
            if accounts:
                logger.debug(f"Fetched {len(accounts)} accounts")
                yield accounts
            else:
                logger.info("No accounts found")
                
        except Exception as e:
            logger.error(f"Error fetching accounts: {e}")
            raise
