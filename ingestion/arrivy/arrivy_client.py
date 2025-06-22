import logging
import json
import asyncio
from datetime import datetime
import aiohttp
from aiohttp import BasicAuth
import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings

logger = logging.getLogger(__name__)

class ArrivyClient:
    """Asynchronous client for interacting with the Arrivy API."""
    
    def __init__(self, api_key=None, auth_key=None, api_url=None):
        self.api_key = api_key or settings.ARRIVY_API_KEY
        self.auth_key = auth_key or settings.ARRIVY_AUTH_KEY
        self.base_url = (api_url or settings.ARRIVY_API_URL).rstrip('/')
        
        # Use header-based authentication for Arrivy API (not Basic Auth)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Auth-Key": self.auth_key,
            "X-Auth-Token": self.api_key
        }
        
        print(f"ArrivyClient initialized with API key: {self.api_key[:8]}...")
    
    async def get_customers(self, page_size=100, page=1, last_sync=None):
        """Get customers from Arrivy API."""
        params = {
            "page_size": page_size,
            "page": page
        }
          # Add date filter if provided
        if last_sync:
            # Convert datetime to Arrivy expected format
            last_sync_str = last_sync.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["updated_after"] = last_sync_str
        
        return await self._make_request("customers", params)
    
    async def get_divisions(self, page_size=100, page=1, last_sync=None, endpoint="crews"):
        """Get divisions from Arrivy API using crews endpoint."""
        params = {
            "page_size": page_size,
            "page": page
        }
        
        # Add date filter if provided
        if last_sync:
            last_sync_str = last_sync.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["updated_after"] = last_sync_str
        
        return await self._make_request(endpoint, params)

    async def get_crews(self, page_size=100, page=1, last_sync=None, endpoint="crews"):
        """Get crews from Arrivy API - alias for get_divisions for backward compatibility."""
        return await self.get_divisions(page_size, page, last_sync, endpoint)
    
    async def get_bookings(self, page_size=100, page=1, last_sync=None, start_date=None, end_date=None):
        """Get bookings from Arrivy API."""
        params = {
            "page_size": page_size,
            "page": page
        }
          # Add date filter if provided
        if last_sync:
            last_sync_str = last_sync.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["updated_after"] = last_sync_str
        
        # Add date range filters for bookings
        if start_date:
            params["start_date"] = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        if end_date:
            params["end_date"] = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        return await self._make_request("bookings", params)  # Use bookings endpoint instead of tasks

    async def get_customer_by_id(self, customer_id):
        """Get a specific customer by ID."""
        return await self._make_request(f"customers/{customer_id}")

    async def get_team_member_by_id(self, team_member_id):
        """Get a specific team member by ID."""
        return await self._make_request(f"team/{team_member_id}")

    async def get_booking_by_id(self, booking_id):
        """Get a specific booking by ID."""
        return await self._make_request(f"tasks/{booking_id}")

    async def get_crew_singular(self, page_size=100, page=1, last_sync=None):
        """Test the crew endpoint (singular) to see difference from crews."""
        params = {
            "page_size": page_size,
            "page": page
        }
        
        # Add date filter if provided
        if last_sync:
            last_sync_str = last_sync.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["updated_after"] = last_sync_str
        
        return await self._make_request("crew", params)

    async def get_all_crew_members(self, page_size=100, page=1, last_sync=None):
        """Get all individual crew members from entities_data across all divisions."""
        # Get all divisions first
        divisions_result = await self.get_crews(page_size, page, last_sync)
        
        all_crew_members = []
        divisions_data = divisions_result.get('data', [])
        
        for division in divisions_data:
            division_name = division.get('name', 'Unknown Division')
            division_id = division.get('id')
            entities_data = division.get('entities_data', [])
            
            if isinstance(entities_data, list):
                for crew_member in entities_data:
                    # Add division context to each crew member
                    crew_member_with_context = crew_member.copy()
                    crew_member_with_context['division_id'] = division_id
                    crew_member_with_context['division_name'] = division_name
                    all_crew_members.append(crew_member_with_context)
        
        return {
            'data': all_crew_members,
            'pagination': divisions_result.get('pagination'),
            'total_divisions': len(divisions_data),
            'total_crew_members': len(all_crew_members)
        }

    async def get_entities(self, page_size=100, page=1, last_sync=None):
        """Get entities (individual crew members) from Arrivy API."""
        params = {
            "page_size": page_size,
            "page": page
        }
        
        # Add date filter if provided
        if last_sync:
            last_sync_str = last_sync.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["updated_after"] = last_sync_str
        
        return await self._make_request("entities", params)

    async def get_entity_by_id(self, entity_id):
        """Get a specific entity by ID."""
        return await self._make_request(f"entities/{entity_id}")

    async def get_groups(self, page_size=100, page=1, last_sync=None):
        """Get groups from Arrivy API using official groups endpoint."""
        params = {
            "page_size": page_size,
            "page": page
        }
        
        # Add date filter if provided
        if last_sync:
            last_sync_str = last_sync.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["updated_after"] = last_sync_str
        
        return await self._make_request("groups", params)

    async def get_group_by_id(self, group_id):
        """Get a specific group by ID."""
        return await self._make_request(f"groups/{group_id}")

    async def _make_request(self, endpoint, params=None):
        """Make an HTTP request to the Arrivy API using header authentication."""
        url = f"{self.base_url}/{endpoint}"
        
        logger.info(f"Making request to: {url}")
        logger.debug(f"Params: {params}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params, timeout=60) as response:
                    status = response.status
                    response_text = await response.text()
                    
                    logger.info(f"Response status: {status}")
                    logger.debug(f"Response body: {response_text[:500]}")
                    
                    if status == 200:
                        try:
                            data = json.loads(response_text)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse JSON response: {response_text}")
                            return {'data': [], 'pagination': None}
                        
                        # Handle Arrivy's response format
                        if isinstance(data, dict):
                            if 'results' in data:
                                # Paginated response
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
                                # Single item response
                                return {'data': data, 'pagination': None}
                        elif isinstance(data, list):
                            # Direct list response
                            return {'data': data, 'pagination': None}
                        else:
                            return {'data': [], 'pagination': None}
                    
                    elif status == 401:
                        logger.error("Arrivy API authentication failed")
                        raise Exception("Authentication failed - check API keys")
                    
                    elif status == 429:
                        logger.warning("Arrivy API rate limit exceeded")
                        raise Exception("Rate limit exceeded")
                    
                    else:
                        logger.error(f"Arrivy API error {status}: {response_text[:500]}")
                        raise Exception(f"API request failed with status {status}")
                        
        except asyncio.TimeoutError:
            logger.error("Arrivy API request timed out")
            raise Exception("Request timed out")
            
        except Exception as e:
            logger.error(f"Error making Arrivy API request: {str(e)}")
            raise

    async def test_connection(self):
        """Test the connection to Arrivy API."""
        try:
            result = await self.get_customers(page_size=1, page=1)
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)

    def test_connection_requests(self):
        """Synchronous connectivity check using requests with header authentication."""
        url = f"{self.base_url}/tasks"
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return True, response.json()
        except Exception as e:
            return False, str(e)

    # Backward compatibility alias
    async def get_team_members(self, page_size=100, page=1, last_sync=None, endpoint="crews"):
        """Get team members from Arrivy API. (Deprecated: use get_crews instead)"""
        return await self.get_crews(page_size, page, last_sync, endpoint)
