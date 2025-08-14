"""
Base Arrivy API Client

Refactored from ingestion/arrivy/arrivy_client.py to follow enterprise patterns.
Implements standardized client interface with proper error handling and rate limiting.
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, AsyncGenerator, Any
import aiohttp
from aiohttp import BasicAuth
import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings

from ingestion.base.client import BaseAPIClient
from ingestion.base.exceptions import APIClientException, RateLimitException, RetryableException
from ingestion.base.retry import RetryConfig, exponential_backoff

logger = logging.getLogger(__name__)

async def async_retry_with_backoff(
    operation,
    config: RetryConfig = None,
    on_retry: callable = None,
    *args,
    **kwargs
):
    """
    Async retry mechanism with exponential backoff
    
    Args:
        operation: Async function to execute
        config: RetryConfig instance
        on_retry: Callback function called on each retry attempt
        *args: Positional arguments for the operation
        **kwargs: Keyword arguments for the operation
    """
    if config is None:
        config = RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=60.0,
            backoff_factor=2.0,
            retryable_exceptions=(APIClientException, RateLimitException, RetryableException, asyncio.TimeoutError)
        )
    
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return await operation(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            # Check if this is the last attempt
            if attempt == config.max_retries:
                logger.error(f"Max retries ({config.max_retries}) exceeded for {operation.__name__}")
                raise
            
            # Check if exception is retryable
            if not isinstance(e, config.retryable_exceptions):
                logger.error(f"Non-retryable exception in {operation.__name__}: {e}")
                raise
            
            # Handle rate limiting
            if isinstance(e, RateLimitException) and e.retry_after:
                delay = e.retry_after
                logger.warning(f"Rate limited, waiting {delay} seconds before retry {attempt + 1}")
            else:
                delay = exponential_backoff(attempt, config)
                logger.warning(f"Retrying {operation.__name__} in {delay:.2f} seconds (attempt {attempt + 1}/{config.max_retries})")
            
            # Call retry callback if provided
            if on_retry:
                on_retry(e, attempt + 1)
            
            await asyncio.sleep(delay)
    
    # This shouldn't be reached, but just in case
    raise last_exception

class ArrivyBaseClient(BaseAPIClient):
    """Base client for Arrivy API operations following enterprise patterns"""
    
    def __init__(self, api_key: Optional[str] = None, auth_key: Optional[str] = None, 
                 api_url: Optional[str] = None, **kwargs):
        super().__init__('arrivy', **kwargs)
        
        self.api_key = api_key or settings.ARRIVY_API_KEY
        self.auth_key = auth_key or settings.ARRIVY_AUTH_KEY
        self.base_url = (api_url or settings.ARRIVY_API_URL).rstrip('/')
        
        # Use header-based authentication for Arrivy API
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Auth-Key": self.auth_key,
            "X-Auth-Token": self.api_key
        }
        
        logger.info(f"ArrivyBaseClient initialized with API key: {self.api_key[:8]}...")
    
    async def test_connection(self) -> tuple[bool, str]:
        """Test the connection to Arrivy API"""
        try:
            # Use a lightweight endpoint to test connectivity
            result = await self._make_request("customers", {"page_size": 1, "page": 1})
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make HTTP request to Arrivy API with retry mechanism and error handling
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            
        Returns:
            Standardized response format: {'data': [...], 'pagination': {...}}
        """
        # Use retry mechanism for robust API calls
        retry_config = RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=60.0,
            backoff_factor=2.0,
            retryable_exceptions=(APIClientException, RateLimitException, RetryableException, asyncio.TimeoutError)
        )
        
        def on_retry_callback(exception, attempt):
            logger.warning(f"API request retry {attempt} for {endpoint}: {exception}")
        
        return await async_retry_with_backoff(
            self._make_request_once,
            config=retry_config,
            on_retry=on_retry_callback,
            endpoint=endpoint,
            params=params
        )
    
    async def _make_request_once(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make a single HTTP request to Arrivy API (without retry logic)
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            
        Returns:
            Standardized response format: {'data': [...], 'pagination': {...}}
        """
        url = f"{self.base_url}/{endpoint}"
        
        logger.debug(f"Making request to: {url}")
        logger.debug(f"Params: {params}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=self.headers, 
                    params=params, 
                    timeout=aiohttp.ClientTimeout(total=120)  # Increased from 60 to 120 seconds
                ) as response:
                    status = response.status
                    response_text = await response.text()
                    
                    logger.debug(f"Response status: {status}")
                    logger.debug(f"Response body (first 500 chars): {response_text[:500]}")
                    
                    if status == 200:
                        return self._parse_response(response_text)
                    elif status == 401:
                        logger.error("Arrivy API authentication failed")
                        raise APIClientException("Authentication failed - check API keys")
                    elif status == 429:
                        logger.warning("Arrivy API rate limit exceeded")
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            try:
                                retry_after = int(retry_after)
                            except ValueError:
                                retry_after = 60  # Default fallback
                        else:
                            retry_after = 60  # Default fallback
                        raise RateLimitException("Rate limit exceeded", retry_after=retry_after)
                    else:
                        logger.error(f"Arrivy API error {status}: {response_text[:500]}")
                        raise APIClientException(f"API request failed with status {status}")
                        
        except asyncio.TimeoutError:
            logger.error("Arrivy API request timed out")
            raise RetryableException("Request timed out")
        except aiohttp.ClientError as e:
            logger.error(f"Network error during Arrivy API request: {str(e)}")
            raise RetryableException(f"Network error: {str(e)}")
        except Exception as e:
            if isinstance(e, (APIClientException, RateLimitException, RetryableException)):
                raise
            logger.error(f"Error making Arrivy API request: {str(e)}")
            raise APIClientException(f"Request failed: {str(e)}")
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Arrivy API response into standardized format"""
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response_text[:1000]}")
            raise APIClientException(f"Invalid JSON response: {str(e)}")
        
        # Handle Arrivy's response format and normalize to standard format
        # Based on the reference script, Arrivy API can return:
        # 1. Direct list of records
        # 2. Dict with list values (need to find the first list)
        # 3. Dict with 'results' key (traditional pagination)
        
        if isinstance(data, list):
            # Direct list response (most common for Arrivy)
            return {'data': data, 'pagination': None}
        elif isinstance(data, dict):
            if 'results' in data:
                # Traditional paginated response
                results = data.get('results', [])
                pagination = {
                    'has_next': data.get('has_next', False),
                    'next_page': data.get('next_page'),
                    'total_count': data.get('total_count', 0),
                    'current_page': data.get('current_page', 1),
                    'page_size': data.get('page_size', 100)
                }
                return {'data': results, 'pagination': pagination}
            else:
                # Dict response - find first list value (Arrivy pattern)
                records = []
                for value in data.values():
                    if isinstance(value, list):
                        records = value
                        break
                
                if not records:
                    # If no list found, treat as single item
                    records = [data] if data else []
                
                return {'data': records, 'pagination': None}
        else:
            return {'data': [], 'pagination': None}
    
    async def fetch_paginated_data(self, endpoint: str, last_sync: Optional[datetime] = None,
                                 page_size: int = 100, **kwargs) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch paginated data with delta sync support
        
        Args:
            endpoint: API endpoint
            last_sync: Last sync timestamp for delta sync
            page_size: Records per page (max 200 recommended)
            **kwargs: Additional parameters
        
        Yields:
            Batches of records
        """
        page = 1
        has_more = True
        
        while has_more:
            params = {
                "page_size": page_size,
                "page": page,
                **kwargs
            }
            
            # Add delta sync filter if provided (though Arrivy API may ignore it)
            if last_sync:
                last_sync_str = last_sync.strftime("%Y-%m-%dT%H:%M:%SZ")
                params["updated_after"] = last_sync_str
            
            try:
                result = await self._make_request(endpoint, params)
                data = result.get('data', [])
                pagination = result.get('pagination')
                
                logger.debug(f"Page {page}: Retrieved {len(data)} records")
                
                if data:
                    yield data
                
                # Arrivy API pagination logic:
                # - Continue until a page returns 0 records (per documentation)
                # - Don't rely on pagination metadata as it may not be present
                if len(data) == 0:
                    logger.debug(f"Page {page} returned 0 records, stopping pagination")
                    has_more = False
                elif len(data) < page_size:
                    logger.debug(f"Page {page} returned {len(data)} < {page_size} records, this might be the last page")
                    # Continue to next page to confirm (some APIs return partial pages)
                
                # Check pagination metadata if available (fallback)
                if pagination:
                    has_pagination_next = pagination.get('has_next', False)
                    if not has_pagination_next:
                        logger.debug(f"Pagination metadata indicates no more pages")
                        has_more = False
                        
            except Exception as e:
                logger.error(f"Error fetching page {page} from {endpoint}: {str(e)}")
                raise
            
            page += 1
    
    # Implementation of abstract methods from BaseAPIClient
    
    async def authenticate(self) -> None:
        """Authenticate with Arrivy API"""
        # Arrivy uses header-based authentication which is already set up in __init__
        # We can test the authentication by making a simple request
        logger.debug("Testing Arrivy API authentication")
        
        try:
            success, message = await self.test_connection()
            if not success:
                raise APIClientException(f"Authentication failed: {message}")
            
            logger.info("Arrivy API authentication successful")
            
        except Exception as e:
            logger.error(f"Arrivy API authentication failed: {e}")
            raise APIClientException(f"Authentication failed: {e}")
    
    def get_rate_limit_headers(self) -> Dict[str, str]:
        """Return rate limit headers for Arrivy API"""
        # Arrivy API doesn't use standard rate limit headers
        # Return empty dict - rate limiting is handled by the API responses
        return {}
