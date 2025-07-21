"""
Base SalesRabbit API client following framework standards
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from ingestion.base.client import BaseAPIClient
from ingestion.base.exceptions import AuthenticationException, RateLimitException

logger = logging.getLogger(__name__)

class SalesRabbitBaseClient(BaseAPIClient):
    """Base client for SalesRabbit API following framework standards"""
    
    def __init__(self, api_token=None, **kwargs):
        base_url = getattr(settings, 'SALESRABBIT_API_URL', 'https://api.salesrabbit.com').rstrip('/')
        super().__init__(base_url=base_url, timeout=60, **kwargs)
        self.api_token = api_token or getattr(settings, 'SALESRABBIT_API_TOKEN', None)
        self.rate_limit_delay = 1.0  # Seconds between requests
        
    async def authenticate(self) -> None:
        """Implement SalesRabbit-specific authentication"""
        if not self.api_token:
            raise AuthenticationException("SalesRabbit API key not configured")
        
        self.headers.update({
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        logger.info(f"SalesRabbit client initialized with token: {self.api_token[:5]}...{self.api_token[-5:]}")
    
    def get_rate_limit_headers(self) -> Dict[str, str]:
        """Return SalesRabbit-specific rate limit headers"""
        return {
            'X-RateLimit-Limit': 'X-RateLimit-Limit',
            'X-RateLimit-Remaining': 'X-RateLimit-Remaining',
            'X-RateLimit-Reset': 'X-RateLimit-Reset',
            'Retry-After': 'Retry-After'
        }
    
    async def handle_rate_limiting(self, response):
        """Handle SalesRabbit rate limiting with exponential backoff"""
        if response.status == 429:
            retry_after = int(response.headers.get('Retry-After', self.rate_limit_delay))
            logger.warning(f"Rate limit exceeded, sleeping for {retry_after} seconds")
            await asyncio.sleep(retry_after)
            raise RateLimitException(f"Rate limit exceeded, retry after {retry_after}s")
        elif response.status == 401:
            raise AuthenticationException("Authentication failed - invalid API token")
        elif response.status >= 500:
            logger.error(f"Server error {response.status}: {await response.text()}")
            raise Exception(f"Server error: {response.status}")
    
    async def _make_paginated_request(self, endpoint: str, params: Dict = None) -> list:
        """Make paginated requests to SalesRabbit API"""
        if params is None:
            params = {}
        
        all_data = []
        page = 1
        page_size = params.get('limit', 1000)
        
        # Use context manager for proper session handling
        async with self as client:
            while True:
                current_params = {**params, 'page': page, 'limit': page_size}
                
                try:
                    response = await client.make_request('GET', endpoint, params=current_params)
                    
                    # Handle different response formats
                    if isinstance(response, list):
                        data = response
                    elif isinstance(response, dict):
                        data = response.get('data', response.get('leads', []))
                    else:
                        data = []
                    
                    if not data:
                        break
                    
                    all_data.extend(data)
                    logger.info(f"Fetched page {page} with {len(data)} records from {endpoint}")
                    
                    # If we got less than page_size, we're done
                    if len(data) < page_size:
                        break
                    
                    page += 1
                    
                    # Add rate limiting delay
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.error(f"Error fetching page {page} from {endpoint}: {e}")
                    raise
        
        logger.info(f"Total records fetched from {endpoint}: {len(all_data)}")
        return all_data
    
    async def _make_limited_paginated_request(self, endpoint: str, params: Dict = None, max_records: int = 0) -> list:
        """Make paginated requests with a maximum record limit"""
        if params is None:
            params = {}
        
        all_data = []
        page = 1
        page_size = params.get('limit', 1000)
        
        # Use context manager for proper session handling
        async with self as client:
            while len(all_data) < max_records:
                current_params = {**params, 'page': page, 'limit': page_size}
                
                try:
                    response = await client.make_request('GET', endpoint, params=current_params)
                    
                    # Handle different response formats
                    if isinstance(response, list):
                        data = response
                    elif isinstance(response, dict):
                        data = response.get('data', response.get('leads', []))
                    else:
                        data = []
                    
                    if not data:
                        break
                    
                    # Add only the records we need to stay within max_records limit
                    remaining_slots = max_records - len(all_data)
                    data_to_add = data[:remaining_slots]
                    all_data.extend(data_to_add)
                    
                    logger.info(f"Fetched page {page} with {len(data_to_add)} records from {endpoint} (total: {len(all_data)}/{max_records})")
                    
                    # If we've reached the limit, break
                    if len(all_data) >= max_records:
                        break
                    
                    # If we got less than page_size, we're done
                    if len(data) < page_size:
                        break
                    
                    page += 1
                    
                    # Add rate limiting delay
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.error(f"Error fetching page {page} from {endpoint}: {e}")
                    raise
        
        logger.info(f"Total records fetched from {endpoint}: {len(all_data)} (limited to {max_records})")
        return all_data
