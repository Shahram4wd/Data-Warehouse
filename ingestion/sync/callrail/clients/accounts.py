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
        Fetch accounts from CallRail API
        
        Args:
            since_date: Optional datetime for delta sync
            **params: Additional query parameters
            
        Yields:
            List[Dict]: Batches of account records
        """
        logger.info("Fetching accounts from CallRail API")
        
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
                endpoint=f"/accounts.json",
                params=query_params,
                **params
            ):
                if batch:
                    logger.debug(f"Fetched {len(batch)} accounts")
                    yield batch
                else:
                    logger.info("No more accounts to fetch")
                    break
                    
        except Exception as e:
            logger.error(f"Error fetching accounts: {e}")
            raise
