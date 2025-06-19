"""
LeadConduit API Client
Handles authentication and API calls to the LeadConduit platform
"""

import os
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timezone
import time

logger = logging.getLogger(__name__)


class LeadConduitClient:
    """Client for interacting with the LeadConduit API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('LEADCONDUIT_API_KEY')
        self.base_url = "https://app.leadconduit.com"
        self.session = requests.Session()
        
        if not self.api_key:
            raise ValueError("LeadConduit API key is required. Set LEADCONDUIT_API_KEY environment variable.")
        
        # Set up authentication
        self.session.auth = HTTPBasicAuth('X', self.api_key)
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        logger.info("LeadConduit client initialized")
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     json_data: Optional[Dict] = None, timeout: int = 30) -> requests.Response:
        """Make HTTP request to LeadConduit API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=timeout
            )
            
            logger.debug(f"{method} {endpoint} - Status: {response.status_code}")
            
            if response.status_code == 401:
                raise Exception("Authentication failed. Check your API key.")
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded. Please wait before making more requests.")
            elif response.status_code >= 400:
                raise Exception(f"API request failed: {response.status_code} - {response.text}")
                
            return response
            
        except requests.exceptions.Timeout:
            raise Exception(f"Request timeout after {timeout} seconds")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error. Check your internet connection.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            response = self._make_request('GET', '/events', params={'limit': 1})
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def get_events(self, limit: int = 100, after_id: Optional[str] = None, 
                   before_id: Optional[str] = None, start: Optional[datetime] = None,
                   end: Optional[datetime] = None, sort: str = 'desc') -> List[Dict[str, Any]]:
        """
        Fetch events from LeadConduit
        
        Args:
            limit: Maximum number of events to return (1-1000)
            after_id: Return events created after this ID
            before_id: Return events created before this ID  
            start: Return events created at or after this time
            end: Return events created at or before this time
            sort: Sort order - 'asc' or 'desc'
        """
        params = {
            'limit': min(limit, 1000),  # Cap at API maximum
            'sort': sort
        }
        
        if after_id:
            params['after_id'] = after_id
        if before_id:
            params['before_id'] = before_id
        if start:
            params['start'] = start.isoformat()
        if end:
            params['end'] = end.isoformat()
        
        response = self._make_request('GET', '/events', params=params)
        return response.json()
    
    def get_events_paginated(self, limit_per_page: int = 1000, max_total: Optional[int] = None,
                           start: Optional[datetime] = None, end: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Fetch all events with automatic pagination
        
        Args:
            limit_per_page: Number of events per API call (max 1000)
            max_total: Maximum total events to fetch (None for unlimited)
            start: Return events created at or after this time
            end: Return events created at or before this time
        """
        all_events = []
        after_id = None
        page = 1
        
        while True:
            logger.info(f"Fetching page {page} (after_id: {after_id})")
            
            # Calculate how many to fetch this round
            remaining = None
            if max_total:
                remaining = max_total - len(all_events)
                if remaining <= 0:
                    break
                limit_per_page = min(limit_per_page, remaining)
            
            events = self.get_events(
                limit=limit_per_page,
                after_id=after_id,
                start=start,
                end=end,
                sort='asc'  # Use ascending for pagination
            )
            
            if not events:
                logger.info("No more events found")
                break
            
            all_events.extend(events)
            logger.info(f"Fetched {len(events)} events (total: {len(all_events)})")
            
            # Set up for next page
            after_id = events[-1]['id']
            page += 1
            
            # Rate limiting - be nice to the API
            time.sleep(0.1)
        
        logger.info(f"Completed pagination: {len(all_events)} total events")
        return all_events
    
    def get_event_by_id(self, event_id: str) -> Dict[str, Any]:
        """Fetch a single event by ID"""
        response = self._make_request('GET', f'/events/{event_id}')
        return response.json()
    
    def search_leads(self, query: str, limit: int = 10, from_offset: int = 0,
                    sort_by: Optional[str] = None, sort_dir: str = 'desc') -> Dict[str, Any]:
        """
        Search for leads using full text search
        
        Args:
            query: Text to search for
            limit: Maximum number of results (max 100)
            from_offset: Starting offset (for pagination)
            sort_by: Field to sort by
            sort_dir: Sort direction ('asc' or 'desc')
        """
        params = {
            'query': query,
            'limit': min(limit, 100),
            'from': from_offset,
            'sort_dir': sort_dir
        }
        
        if sort_by:
            params['sort_by'] = sort_by
        
        response = self._make_request('GET', '/search/leads', params=params)
        return response.json()
    
    def get_event_statistics(self, start: Optional[datetime] = None, 
                           end: Optional[datetime] = None, 
                           event_type: str = 'source') -> List[Dict[str, Any]]:
        """
        Get event statistics
        
        Args:
            start: Count events created at or after this time
            end: Count events created at or before this time
            event_type: Type of events to count (source, recipient, etc.)
        """
        params = {
            'type': event_type
        }
        
        if start:
            params['start'] = start.isoformat()
        if end:
            params['end'] = end.isoformat()
        
        response = self._make_request('GET', '/events/stats', params=params)
        return response.json()
    
    def post_events_query(self, query_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Post a complex events query for exports
        
        Args:
            query_data: Query parameters as JSON
        """
        response = self._make_request('POST', '/events', json_data=query_data)
        return response.json()
