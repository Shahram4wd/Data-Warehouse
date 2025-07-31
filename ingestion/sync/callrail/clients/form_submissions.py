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
        account_id: str,
        since_date: Optional[datetime] = None,
        **params
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch form submissions from CallRail API
        
        Args:
            account_id: CallRail account ID
            since_date: Optional datetime for delta sync
            **params: Additional query parameters
            
        Yields:
            List[Dict]: Batches of form submission records
        """
        logger.info(f"Fetching form submissions for account {account_id}")
        
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
                endpoint=f"/accounts/{account_id}/form_submissions.json",
                params=query_params,
                **params
            ):
                if batch:
                    logger.debug(f"Fetched {len(batch)} form submissions")
                    yield batch
                else:
                    logger.info("No more form submissions to fetch")
                    break
                    
        except Exception as e:
            logger.error(f"Error fetching form submissions: {e}")
            raise
