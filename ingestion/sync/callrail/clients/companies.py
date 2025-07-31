"""
CallRail companies client for fetching company data
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from .base import CallRailBaseClient

logger = logging.getLogger(__name__)


class CompaniesClient(CallRailBaseClient):
    """Client for CallRail companies API endpoint"""
    
    def get_date_filter_field(self) -> Optional[str]:
        """CallRail companies use 'created_at' for date filtering"""
        return 'created_at'
    
    def extract_data_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract companies data from CallRail API response"""
        return response.get('companies', [])
    
    async def fetch_companies(
        self, 
        account_id: str,
        since_date: Optional[datetime] = None,
        **params
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch companies from CallRail API
        
        Args:
            account_id: CallRail account ID
            since_date: Only fetch companies since this date (for delta sync)
            **params: Additional query parameters
        """
        endpoint = f'a/{account_id}/companies.json'
        
        # Default parameters for companies
        default_params = {
            'per_page': 100,
        }
        
        # Merge with provided parameters
        company_params = {**default_params, **params}
        
        logger.info(f"Fetching CallRail companies for account {account_id}")
        if since_date:
            logger.info(f"Delta sync since: {since_date}")
        
        async for batch in self.fetch_paginated_data(endpoint, since_date, **company_params):
            yield batch
    
    async def get_company_by_id(self, account_id: str, company_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific company by ID"""
        endpoint = f'a/{account_id}/companies/{company_id}.json'
        
        try:
            response = await self.make_request('GET', endpoint)
            return response
        except Exception as e:
            logger.error(f"Failed to fetch company {company_id}: {e}")
            return None
