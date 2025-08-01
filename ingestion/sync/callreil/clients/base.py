"""
Base CallReil API client following CRM sync guide architecture
"""
import logging
import asyncio
import os
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from django.conf import settings
from ingestion.base.client import BaseAPIClient
from ingestion.base.exceptions import APIException, RateLimitError

logger = logging.getLogger(__name__)


class CallReilBaseClient(BaseAPIClient):
    """Base CallReil API client with common functionality following CRM sync guide"""
    
    def __init__(self, api_token=None):
        super().__init__(base_url="https://api.callrail.com/v3", timeout=60)
        self.api_token = api_token or settings.CALLRAIL_API_KEY
        if not self.api_token:
            raise ValueError(
                "CallRail API key is required. Set CALLRAIL_API_KEY environment variable "
                "or pass api_token parameter."
            )
        
    async def authenticate(self) -> None:
        """Set up authentication headers following CallRail API requirements"""
        self.headers.update({
            "Authorization": f'Token token="{self.api_token}"',
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        logger.info(f"CallReil client initialized with token: {self.api_token[:5]}...{self.api_token[-5:]}")
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Override make_request to handle CallRail-specific errors and rate limiting"""
        try:
            response = await super().make_request(method, endpoint, **kwargs)
            return response
        except APIException as e:
            # Handle CallRail-specific error responses
            error_str = str(e)
            
            # Handle rate limiting (CallRail uses HTTP 429)
            if "HTTP 429" in error_str or "rate limit" in error_str.lower():
                logger.warning("CallRail rate limit hit, implementing backoff")
                await asyncio.sleep(60)  # CallRail rate limit reset is typically 1 minute
                raise RateLimitError("CallRail API rate limit exceeded")
                
            # Handle authentication errors
            elif "HTTP 401" in error_str or "HTTP 403" in error_str:
                logger.error(f"CallRail authentication failed - check API token")
                raise APIException(f"CallRail authentication failed: {error_str}")
                
            # Handle not found errors
            elif "HTTP 404" in error_str:
                logger.warning(f"CallRail resource not found: {endpoint}")
                raise APIException(f"CallRail resource not found: {endpoint}")
                
            # Re-raise other exceptions
            else:
                logger.error(f"CallRail API error: {error_str}")
                raise
    
    async def fetch_paginated_data(
        self, 
        endpoint: str, 
        since_date: Optional[datetime] = None,
        **params
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch paginated data from CallRail API with delta sync support
        Following CRM sync guide pagination patterns
        """
        page = 1
        per_page = params.get('per_page', 100)
        
        # Add date filtering for delta sync
        if since_date:
            # CallRail uses different date field names for different endpoints
            date_field = self.get_date_filter_field()
            if date_field:
                # Format datetime for CallRail API (ISO 8601)
                params[date_field] = since_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                logger.info(f"CallRail delta sync: filtering {date_field} >= {since_date}")
        
        while True:
            # Set pagination parameters
            current_params = {
                'page': page,
                'per_page': per_page,
                **params
            }
            
            logger.debug(f"Fetching CallRail {endpoint} page {page}")
            
            try:
                response = await self.make_request('GET', endpoint, params=current_params)
                
                # Extract data from response
                data = self.extract_data_from_response(response)
                
                if not data:
                    logger.info(f"No more data on page {page}, ending pagination")
                    break
                
                logger.info(f"Retrieved {len(data)} records from page {page}")
                yield data
                
                # Check if we should continue pagination
                if not self.should_continue_pagination(response, data, per_page):
                    break
                    
                page += 1
                
                # Implement rate limiting between requests
                await self.rate_limit_delay()
                
            except RateLimitError:
                logger.warning("Rate limit hit during pagination, waiting before retry")
                await asyncio.sleep(60)
                continue
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                raise
    
    def get_date_filter_field(self) -> Optional[str]:
        """
        Get the appropriate date field for filtering - override in subclasses
        CallRail uses different field names for different endpoints
        """
        return None
    
    def extract_data_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract data array from CallRail API response - override in subclasses"""
        # Default extraction - most CallRail endpoints use this pattern
        for key in ['calls', 'companies', 'accounts', 'trackers', 'form_submissions', 
                   'text_messages', 'tags', 'users']:
            if key in response:
                return response[key]
        
        # Fallback to direct response if it's already a list
        if isinstance(response, list):
            return response
            
        return []
    
    def should_continue_pagination(
        self, 
        response: Dict[str, Any], 
        data: List[Dict[str, Any]], 
        per_page: int
    ) -> bool:
        """Determine if pagination should continue based on CallRail response"""
        # Check if we got fewer records than requested (indicates last page)
        if len(data) < per_page:
            return False
            
        # Check CallRail pagination metadata
        if 'total_pages' in response and 'page' in response:
            current_page = response.get('page', 1)
            total_pages = response.get('total_pages', 1)
            return current_page < total_pages
            
        # Default: continue if we got a full page
        return len(data) == per_page
    
    async def rate_limit_delay(self) -> None:
        """Implement rate limiting delay between requests"""
        # CallRail allows up to 200 requests per minute
        # Add small delay to be conservative
        await asyncio.sleep(0.3)  # ~200 requests per minute
    
    async def get_account_id(self) -> str:
        """Get the first available account ID for the authenticated user"""
        try:
            response = await self.make_request('GET', 'a.json')
            accounts = response.get('accounts', [])
            
            if not accounts:
                raise APIException("No CallRail accounts found for this API key")
                
            account_id = accounts[0]['id']
            logger.info(f"Using CallRail account ID: {account_id}")
            return account_id
            
        except Exception as e:
            logger.error(f"Failed to get CallRail account ID: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """Test the API connection and authentication"""
        try:
            await self.get_account_id()
            logger.info("CallRail API connection test successful")
            return True
        except Exception as e:
            logger.error(f"CallRail API connection test failed: {e}")
            return False
