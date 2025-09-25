"""
Base Arrivy API Client

Refactored from ingestion/arrivy/arrivy_client.py to follow enterprise patterns.
Implements standardized client interface with proper error handling and rate limiting.
"""

import logging
import json
import asyncio
import time
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
            max_retries=5,
            initial_delay=1.0,
            max_delay=120.0,
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
        
        # Performance optimization: Use persistent session with connection pooling
        connector = aiohttp.TCPConnector(
            limit=20,  # Total connection limit
            limit_per_host=5,  # Per-host connection limit
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            enable_cleanup_closed=True,
            keepalive_timeout=60,
            force_close=False
        )
        
        timeout = aiohttp.ClientTimeout(
            total=60,  # Reduced from 120 to 60 seconds
            connect=10,  # Connection timeout
            sock_read=30  # Socket read timeout
        )
        
        try:
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers
            ) as session:
                start_time = time.time()
                async with session.get(url, params=params) as response:
                    end_time = time.time()
                    response_time = end_time - start_time
                    logger.debug(f"API request took {response_time:.2f} seconds")
                    
                    status = response.status
                    response_text = await response.text()
                    
                    logger.debug(f"Response status: {status}")
                    logger.debug(f"Response body (first 500 chars): {response_text[:500]}")
                    
                    if status == 200:
                        result = self._parse_response(response_text)
                        logger.debug(f"Parsed {len(result.get('data', []))} records in {response_time:.2f}s")
                        return result
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
        
        NOTE: Arrivy API appears to ignore page_size parameter and returns ~500 records per page.
        We'll optimize by using larger effective page sizes and chunking the results.
        
        Args:
            endpoint: API endpoint
            last_sync: Last sync timestamp for delta sync
            page_size: Desired records per batch (will chunk API response)
            **kwargs: Additional parameters
        
        Yields:
            Batches of records (chunked to requested page_size)
        """
        page = 1
        has_more = True
        
        logger.info(f"Starting pagination for {endpoint} with requested page_size={page_size}")
        
        while has_more:
            # Since Arrivy API ignores page_size, request larger pages
            # to reduce API calls and improve performance
            api_params = {
                "page_size": 500,  # Use API's natural page size
                "page": page,
                **kwargs
            }
            
            # Add delta sync filter if provided - prefer 'from'/'to' parameters over 'updated_after'
            # The 'from'/'to' parameters should be passed in kwargs, not added here
            if last_sync and 'from' not in kwargs and 'to' not in kwargs:
                # Fallback to updated_after only if 'from'/'to' not already specified
                last_sync_str = last_sync.strftime("%Y-%m-%dT%H:%M:%SZ")
                api_params["updated_after"] = last_sync_str
                logger.debug(f"Using fallback updated_after parameter: {last_sync_str}")
            elif 'from' in kwargs and 'to' in kwargs:
                logger.debug(f"Using from/to range parameters for delta sync")
            
            try:
                start_time = time.time()
                result = await self._make_request(endpoint, api_params)
                request_time = time.time() - start_time
                
                data = result.get('data', [])
                pagination = result.get('pagination')
                
                logger.info(f"Page {page}: Retrieved {len(data)} records in {request_time:.2f}s")
                
                if data:
                    # Chunk the large API response into requested page_size batches
                    for i in range(0, len(data), page_size):
                        chunk = data[i:i + page_size]
                        logger.debug(f"Yielding chunk of {len(chunk)} records")
                        yield chunk
                
                # Arrivy API pagination logic:
                # - Continue until a page returns 0 records
                # - Don't rely on pagination metadata as it may not be present
                if len(data) == 0:
                    logger.info(f"Page {page} returned 0 records, stopping pagination")
                    has_more = False
                elif len(data) < 500:  # Less than expected API page size
                    logger.info(f"Page {page} returned {len(data)} < 500 records, likely last page")
                    # This might be the last page, but check next page to confirm
                
                # Check pagination metadata if available (fallback)
                if pagination:
                    has_pagination_next = pagination.get('has_next', False)
                    if not has_pagination_next:
                        logger.info(f"Pagination metadata indicates no more pages")
                        has_more = False
                        
            except Exception as e:
                logger.error(f"Error fetching page {page} from {endpoint}: {str(e)}")
                raise
            
            page += 1
    
    async def fetch_concurrent_pages(self, endpoint: str, start_page: int = 1, max_pages: int = 5,
                                   page_size: int = 500, **kwargs) -> List[List[Dict]]:
        """
        Fetch multiple pages concurrently for maximum performance
        
        WARNING: Use carefully to avoid overwhelming the API
        
        Args:
            endpoint: API endpoint
            start_page: Starting page number
            max_pages: Maximum number of pages to fetch concurrently
            page_size: Records per page
            **kwargs: Additional parameters
        
        Returns:
            List of page results (each containing list of records)
        """
        logger.info(f"Fetching {max_pages} pages concurrently from {endpoint}")
        
        async def fetch_single_page(page_num: int) -> List[Dict]:
            """Fetch a single page"""
            params = {
                "page_size": page_size,
                "page": page_num,
                **kwargs
            }
            
            try:
                result = await self._make_request(endpoint, params)
                data = result.get('data', [])
                logger.debug(f"Concurrent page {page_num}: {len(data)} records")
                return data
            except Exception as e:
                logger.error(f"Error fetching concurrent page {page_num}: {str(e)}")
                return []
        
        # Create concurrent tasks for multiple pages
        tasks = []
        for page_num in range(start_page, start_page + max_pages):
            task = fetch_single_page(page_num)
            tasks.append(task)
        
        # Execute all requests concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Process results and handle exceptions
        valid_results = []
        total_records = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Concurrent page {start_page + i} failed: {result}")
            else:
                valid_results.append(result)
                total_records += len(result)
        
        logger.info(f"Concurrent fetch: {len(valid_results)} pages, {total_records} records in {total_time:.2f}s")
        return valid_results
    
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
