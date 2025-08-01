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
        since_date: Optional[datetime] = None,
        **params
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch companies from CallRail API for all accessible accounts
        
        Args:
            since_date: Only fetch companies since this date (for delta sync)
            **params: Additional query parameters
        """
        logger.info("Fetching CallRail companies for all accessible accounts")
        
        # First, get all accounts
        accounts_response = await self.make_request('GET', 'a.json', params={})
        accounts = accounts_response.get('accounts', [])
        
        if not accounts:
            logger.warning("No accounts found")
            return
        
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

        # Fetch companies for each account
        for account in accounts:
            account_id = account.get('id')
            if not account_id:
                continue
                
            try:
                endpoint = f'a/{account_id}/companies.json'
                logger.debug(f"Fetching companies for account {account_id}")
                
                response = await self.make_request('GET', endpoint, params=query_params)
                companies = self.extract_data_from_response(response)
                
                if companies:
                    logger.debug(f"Fetched {len(companies)} companies for account {account_id}")
                    yield companies
                else:
                    logger.debug(f"No companies found for account {account_id}")
                    
            except Exception as e:
                logger.error(f"Error fetching companies for account {account_id}: {e}")
                continue
    
    async def get_company_by_id(self, account_id: str, company_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific company by ID"""
        endpoint = f'a/{account_id}/companies/{company_id}.json'
        
        try:
            response = await self.make_request('GET', endpoint)
            return response
        except Exception as e:
            logger.error(f"Failed to fetch company {company_id}: {e}")
            return None
