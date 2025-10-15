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
        page = 0 if '/users' in endpoint else 1  # SalesRabbit users API uses 0-indexed pages
        page_size = params.get('limit', 1000)
        max_pages = 1000  # Safety limit to prevent infinite loops
        previous_data_hash = None  # Track duplicate responses
        
        # Use context manager for proper session handling
        async with self as client:
            while page < max_pages:  # Use < instead of <= for 0-indexed pagination
                # Different endpoints use different pagination parameters
                if '/users' in endpoint:
                    current_params = {**params, 'page': page, 'limit': page_size}
                else:
                    current_params = {**params, 'page': page, 'limit': page_size}
                
                try:
                    response = await client.make_request('GET', endpoint, params=current_params)
                    
                    # Handle different response formats
                    if isinstance(response, list):
                        data = response
                    elif isinstance(response, dict):
                        data = response.get('data', response.get('leads', response.get('users', [])))
                    else:
                        data = []
                    
                    if not data:
                        logger.info(f"No data returned on page {page}, ending pagination")
                        break
                    
                    # Check for duplicate responses (API returning same data on every page)
                    if '/users' in endpoint and len(data) > 0:
                        # Create a hash of all user IDs to detect exact duplicates
                        current_ids = set(user.get('id') for user in data if user.get('id'))
                        current_data_hash = f"{len(data)}-{min(current_ids) if current_ids else 'none'}-{max(current_ids) if current_ids else 'none'}"
                        
                        if previous_data_hash == current_data_hash and page > 1:
                            logger.warning(f"Detected identical response on page {page} (same {len(data)} users as page {page-1}). "
                                         f"SalesRabbit Users API appears to return all users on every page regardless of pagination.")
                            logger.info(f"Total unique users available: {len(data)}. Stopping pagination to avoid duplicates.")
                            break
                        previous_data_hash = current_data_hash
                    
                    all_data.extend(data)
                    logger.info(f"Page {page}: fetched {len(data)} records")
                    
                    # Enhanced termination conditions
                    if '/users' in endpoint:
                        # For users endpoint: if we get all users (less than limit), we're likely done
                        # But also check if this looks like "all users" being returned every time
                        if len(data) < page_size:
                            logger.info(f"Got {len(data)} records (less than limit {page_size}), ending pagination")
                            break
                        elif page > 1 and len(data) == len(all_data) // page:
                            # If each page returns the same number of records and it looks like total/page_count
                            logger.warning(f"Suspicious pagination pattern detected - each page returning {len(data)} records")
                    else:
                        # For other endpoints: standard pagination logic
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
        page = 0 if '/users' in endpoint else 1  # SalesRabbit users API uses 0-indexed pages
        # Use the limit from params directly for true pagination testing
        page_size = params.get('limit', 100)
        max_pages = 1000  # Safety limit to prevent infinite loops
        previous_data_hash = None  # Track duplicate responses
        
        # Use context manager for proper session handling
        async with self as client:
            while len(all_data) < max_records and page < max_pages:  # Use < for 0-indexed users
                # Different endpoints use different pagination parameters
                if '/users' in endpoint:
                    current_params = {**params, 'page': page, 'limit': page_size}
                else:
                    current_params = {**params, 'page': page, 'limit': page_size}
                
                try:
                    response = await client.make_request('GET', endpoint, params=current_params)
                    
                    # Handle different response formats
                    if isinstance(response, list):
                        data = response
                    elif isinstance(response, dict):
                        data = response.get('data', response.get('leads', response.get('users', [])))
                    else:
                        data = []
                    
                    if not data:
                        logger.info(f"No data returned on page {page}, ending pagination")
                        break
                    
                    # Check for duplicate responses (API returning same data on every page)
                    if '/users' in endpoint and len(data) > 0:
                        # Create a hash of all user IDs to detect exact duplicates
                        current_ids = set(user.get('id') for user in data if user.get('id'))
                        current_data_hash = f"{len(data)}-{min(current_ids) if current_ids else 'none'}-{max(current_ids) if current_ids else 'none'}"
                        
                        if previous_data_hash == current_data_hash and page > 1:
                            logger.warning(f"Detected identical response on page {page} (same {len(data)} users as page {page-1}). "
                                         f"SalesRabbit Users API appears to return all users on every page regardless of pagination.")
                            logger.info(f"Total unique users available: {len(data)}. Stopping pagination to avoid duplicates.")
                            # Don't add duplicate data, just break
                            break
                        previous_data_hash = current_data_hash
                    
                    # Add only the records we need to stay within max_records limit
                    remaining_slots = max_records - len(all_data)
                    data_to_add = data[:remaining_slots]
                    all_data.extend(data_to_add)
                    
                    logger.info(f"Fetched page {page} with {len(data_to_add)} records from {endpoint} (total: {len(all_data)}/{max_records})")
                    
                    # If we've reached the limit, break
                    if len(all_data) >= max_records:
                        break
                    
                    # Enhanced termination conditions
                    if '/users' in endpoint:
                        # For users endpoint: if we get all users (less than limit), we're likely done
                        if len(data) < page_size:
                            logger.info(f"Got {len(data)} records (less than limit {page_size}), ending pagination")
                            break
                    else:
                        # For other endpoints: standard pagination logic
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

    async def _make_paginated_request_with_headers(self, endpoint: str, params: Dict = None, extra_headers: Dict = None) -> list:
        """Make paginated requests to SalesRabbit API with custom headers"""
        if params is None:
            params = {}
        if extra_headers is None:
            extra_headers = {}
        
        all_data = []
        page = 1
        page_size = params.get('limit', 1000)
        
        # Use context manager for proper session handling
        async with self as client:
            while True:
                current_params = {**params, 'page': page, 'limit': page_size}
                
                try:
                    response = await client.make_request('GET', endpoint, params=current_params, headers=extra_headers)
                    
                    # Handle different response formats
                    if isinstance(response, list):
                        data = response
                    elif isinstance(response, dict):
                        data = response.get('data', response.get('leads', response.get('users', [])))
                    else:
                        data = []
                    
                    if not data:
                        break
                    
                    all_data.extend(data)
                    logger.info(f"Fetched page {page} with {len(data)} records from {endpoint} (with headers)")
                    
                    # If we got less than page_size, we're done
                    if len(data) < page_size:
                        break
                    
                    page += 1
                    
                    # Add rate limiting delay
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.error(f"Error fetching page {page} from {endpoint}: {e}")
                    raise
        
        logger.info(f"Total records fetched from {endpoint}: {len(all_data)} (with headers)")
        return all_data

    async def _make_limited_paginated_request_with_headers(self, endpoint: str, params: Dict = None, max_records: int = 0, extra_headers: Dict = None) -> list:
        """Make paginated requests with a maximum record limit and custom headers"""
        if params is None:
            params = {}
        if extra_headers is None:
            extra_headers = {}
        
        all_data = []
        page = 1
        page_size = params.get('limit', 1000)
        
        # Use context manager for proper session handling
        async with self as client:
            while len(all_data) < max_records:
                current_params = {**params, 'page': page, 'limit': page_size}
                
                try:
                    response = await client.make_request('GET', endpoint, params=current_params, headers=extra_headers)
                    
                    # Handle different response formats
                    if isinstance(response, list):
                        data = response
                    elif isinstance(response, dict):
                        data = response.get('data', response.get('leads', response.get('users', [])))
                    else:
                        data = []
                    
                    if not data:
                        break
                    
                    # Add only the records we need to stay within max_records limit
                    remaining_slots = max_records - len(all_data)
                    data_to_add = data[:remaining_slots]
                    all_data.extend(data_to_add)
                    
                    logger.info(f"Fetched page {page} with {len(data_to_add)} records from {endpoint} (total: {len(all_data)}/{max_records}, with headers)")
                    
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
        
        logger.info(f"Total records fetched from {endpoint}: {len(all_data)} (limited to {max_records}, with headers)")
        return all_data
