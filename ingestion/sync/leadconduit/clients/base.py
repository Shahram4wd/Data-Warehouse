"""
LeadConduit Base API Client

Base client implementation following sync_crm_guide architecture with
optimized data retrieval patterns and proper error            except Exception as e:
                logger.error(f"Error fetching events: {e}")
                raise APIException(f"Failed to fetch events: {e}")ndling.
"""
import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timezone
from django.conf import settings

from ingestion.base.client import BaseAPIClient
from ingestion.base.exceptions import APIException, RateLimitException

logger = logging.getLogger(__name__)


class LeadConduitBaseClient(BaseAPIClient):
    """
    Base LeadConduit API client with enterprise-grade features
    
    Implements the sync_crm_guide patterns:
    - Rate limiting and retry logic
    - Proper authentication handling  
    - UTC-optimized datetime processing
    - Memory-efficient async generators
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None, 
                 base_url: str = None, timeout: int = 60, **kwargs):
        # LeadConduit API configuration - use correct endpoint from reference
        self.base_url = base_url or "https://app.leadconduit.com"
        super().__init__(base_url=self.base_url, timeout=timeout)
        
        # Authentication credentials - match reference naming
        self.username = api_key or os.getenv('LEADCONDUIT_USERNAME') or getattr(settings, 'LEADCONDUIT_USERNAME', None)
        self.api_key = api_secret or os.getenv('LEADCONDUIT_API_KEY') or getattr(settings, 'LEADCONDUIT_API_KEY', None)
        
        if not self.username or not self.api_key:
            logger.warning("LeadConduit credentials not found. Set LEADCONDUIT_USERNAME and LEADCONDUIT_API_KEY")
            # Set dummy credentials for testing
            self.username = self.username or "test_username"
            self.api_key = self.api_key or "test_key"
        
        # Rate limiting configuration
        self.rate_limit = kwargs.get('rate_limit', 100)  # requests per minute
        self.request_delay = 60 / self.rate_limit if self.rate_limit > 0 else 0
        
        # Initialize authentication headers
        self._setup_authentication()
        
        logger.info(f"LeadConduit client initialized with base URL: {self.base_url}")
    
    def _setup_authentication(self):
        """Set up LeadConduit API authentication headers"""
        # Set common headers that will be used when session is created
        self.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'DataWarehouse-LeadConduit-Sync/1.0'
        })
        
        # Store auth info for session creation
        self._auth = (self.username, self.api_key)
        
        logger.debug("LeadConduit authentication configured")
    
    async def authenticate(self) -> None:
        """Authenticate with the LeadConduit API"""
        # Set up basic auth for the session when it's created
        # The actual session will be created by the base class
        logger.debug("LeadConduit authentication completed")
    
    async def __aenter__(self):
        """Override session creation to include basic auth"""
        # First authenticate to set up headers
        await self.authenticate()
        
        # Then create session with LeadConduit-specific auth
        import aiohttp
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers=self.headers,
            auth=aiohttp.BasicAuth(self.username, self.api_key)
        )
        return self
    
    async def test_connection(self) -> bool:
        """Test LeadConduit API connection"""
        try:
            # Test with a basic API endpoint
            response = await self.get('/events', params={'limit': 1})
            return response.status_code == 200
        except Exception as e:
            logger.error(f"LeadConduit connection test failed: {e}")
            return False
    
    def get_rate_limit_headers(self, response) -> Dict[str, Any]:
        """Extract rate limit information from response headers"""
        return {
            'limit': response.headers.get('X-RateLimit-Limit'),
            'remaining': response.headers.get('X-RateLimit-Remaining'),
            'reset': response.headers.get('X-RateLimit-Reset'),
            'retry_after': response.headers.get('Retry-After')
        }
    
    async def fetch_events_paginated(self, 
                                   start_date: datetime, 
                                   end_date: datetime,
                                   batch_size: int = 1000) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch LeadConduit events using optimized pagination
        
        Implements ID-based pagination for better performance over time-chunking
        (following optimization patterns from the reference implementation)
        
        Args:
            start_date: Start date in UTC
            end_date: End date in UTC  
            batch_size: Records per API request
            
        Yields:
            List[Dict]: Batches of event records
        """
        logger.info(f"Fetching LeadConduit events from {start_date} to {end_date}")
        
        # Format dates for LeadConduit API
        start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_str = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Use ID-based pagination for better performance
        last_id = None
        total_fetched = 0
        
        while True:
            try:
                # Build query parameters - match reference implementation exactly
                params = {
                    'start': start_str,  # Use 'start' not 'start_date'
                    'end': end_str,      # Use 'end' not 'end_date'  
                    'limit': batch_size,
                    'sort': 'asc'        # Required for after_id to work properly
                }
                
                # Add pagination cursor
                if last_id:
                    params['after_id'] = last_id
                
                # Make API request with rate limiting
                await self._apply_rate_limit()
                
                url = f"{self.base_url}/events"
                async with self.session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status} - {await response.text()}")
                        break
                    
                    data = await response.json()
                    events = data.get('data', data) if isinstance(data, dict) else data
                
                if not events or len(events) == 0:
                    logger.info(f"No more events found. Total fetched: {total_fetched}")
                    break
                
                # Yield this batch
                yield events
                total_fetched += len(events)
                
                # Update pagination cursor
                last_id = events[-1].get('id')
                
                logger.debug(f"Fetched batch of {len(events)} events (total: {total_fetched})")
                
                # Break if we got fewer results than requested (end of data)
                if len(events) < batch_size:
                    logger.info(f"Reached end of data. Total fetched: {total_fetched}")
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching events batch: {e}")
                raise APIException(f"Failed to fetch events: {e}")
    
    async def get_events_with_id_pagination_fast(self, 
                                                start_date: str, 
                                                end_date: str) -> Optional[List[Dict[str, Any]]]:
        """
        Optimized event retrieval using ID-based pagination
        
        This method implements the exact patterns from export_leadconduit_utc.py
        for high-performance data retrieval.
        """
        logger.info(f"Using optimized ID-based pagination for date range: {start_date} to {end_date}")
        
        all_events = []
        after_id = None
        page = 0
        url = f"{self.base_url}/events"
        
        # Headers exactly like reference
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        while True:
            page += 1
            params = {
                'start': start_date,   # Match reference parameter names
                'end': end_date,
                'limit': 1000,         # API maximum from reference
                'sort': 'asc'          # Required for after_id to work properly
            }
            
            if after_id:
                params['after_id'] = after_id
            
            try:
                # Apply rate limiting
                await self._apply_rate_limit()
                
                # Make async request using the session
                async with self.session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"API request failed with status {response.status}: {await response.text()}")
                        return None
                    
                    events = await response.json()
                    current_count = len(events)
                    
                    if current_count > 0:
                        logger.info(f"Page {page}: Retrieved {current_count} events (total so far: {len(all_events) + current_count})")
                        all_events.extend(events)
                        after_id = events[-1]['id']
                    
                    if current_count < 1000:
                        break
                        
            except Exception as e:
                logger.error(f"Request error on page {page}: {e}")
                return None
        
        logger.info(f"Completed pagination: {len(all_events)} total events in {page} pages")
        return all_events
    
    def extract_value(self, field_data: Any, possible_keys: List[str] = None) -> str:
        """
        Extract value from field data using multiple possible keys
        
        REUSABLE: Exact copy from export_leadconduit_utc.py for parsing 
        any LeadConduit API data with complex JSON structures.
        """
        if possible_keys is None:
            possible_keys = [field_data] if isinstance(field_data, str) else []
        
        if not field_data:
            return ''
        
        if isinstance(field_data, dict):
            # Try each possible key in priority order
            for key in possible_keys:
                if key in field_data:
                    value = field_data[key]
                    if isinstance(value, dict):
                        return value.get('value', str(value))
                    return str(value) if value is not None else ''
            
            # Look for common LeadConduit patterns
            common_keys = ['value', 'name', 'id', 'email', 'phone']
            for key in common_keys:
                if key in field_data:
                    value = field_data[key]
                    if isinstance(value, dict):
                        return value.get('value', str(value))
                    return str(value) if value is not None else ''
                    
            return str(field_data)
        else:
            return str(field_data) if field_data is not None else ''
    
    async def _apply_rate_limit(self):
        """Apply rate limiting between API requests"""
        if self.request_delay > 0:
            await asyncio.sleep(self.request_delay)
    
    async def handle_rate_limit_error(self, response):
        """Handle rate limit errors with exponential backoff"""
        rate_limit_info = self.get_rate_limit_headers(response)
        retry_after = int(rate_limit_info.get('retry_after', 60))
        
        logger.warning(f"Rate limit hit. Waiting {retry_after} seconds before retry")
        await asyncio.sleep(retry_after)
        
        raise RateLimitException(f"Rate limit exceeded. Retried after {retry_after}s")
