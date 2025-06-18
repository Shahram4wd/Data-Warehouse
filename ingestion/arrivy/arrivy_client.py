import logging
import json
from datetime import datetime
import aiohttp
from django.conf import settings

logger = logging.getLogger(__name__)

class ArrivyClient:
    """Asynchronous client for interacting with the Arrivy API."""
    
    def __init__(self, api_key=None, auth_key=None, api_url=None):
        self.api_key = api_key or settings.ARRIVY_API_KEY
        self.auth_key = auth_key or settings.ARRIVY_AUTH_KEY
        self.base_url = api_url or settings.ARRIVY_API_URL
        
        self.headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key,
            "X-AUTH-KEY": self.auth_key
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
    
    async def get_team_members(self, page_size=100, page=1, last_sync=None):
        """Get team members from Arrivy API."""
        params = {
            "page_size": page_size,
            "page": page
        }
        
        # Add date filter if provided
        if last_sync:
            last_sync_str = last_sync.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["updated_after"] = last_sync_str
        
        return await self._make_request("team", params)
    
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
        
        return await self._make_request("tasks", params)  # Arrivy calls bookings "tasks"
    
    async def get_customer_by_id(self, customer_id):
        """Get a specific customer by ID."""
        return await self._make_request(f"customers/{customer_id}")
    
    async def get_team_member_by_id(self, team_member_id):
        """Get a specific team member by ID."""
        return await self._make_request(f"team/{team_member_id}")
    
    async def get_booking_by_id(self, booking_id):
        """Get a specific booking by ID."""
        return await self._make_request(f"tasks/{booking_id}")
    
    async def _make_request(self, endpoint, params=None):
        """Make an HTTP request to the Arrivy API."""
        url = f"{self.base_url.rstrip('/')}/{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers, params=params, timeout=60) as response:
                    status = response.status
                    
                    if status == 200:
                        data = await response.json()
                        
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
                        response_text = await response.text()
                        logger.error(f"Arrivy API error {status}: {response_text[:500]}")
                        raise Exception(f"API request failed with status {status}")
                        
            except aiohttp.ClientTimeout:
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
