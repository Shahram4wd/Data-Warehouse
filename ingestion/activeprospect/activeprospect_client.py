import asyncio
import aiohttp
import logging
from datetime import datetime
from django.conf import settings
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ActiveProspectClient:
    """Client for ActiveProspect LeadConduit API using the user's provided authentication"""
    
    def __init__(self):
        self.api_token = settings.ACTIVEPROSPECT_API_TOKEN
        self.base_url = settings.ACTIVEPROSPECT_BASE_URL.rstrip('/')
        
        # HTTP Basic Auth with "X" as username and API token as password
        # Following the user's example: HTTPBasicAuth("X", API_KEY)
        self.auth = aiohttp.BasicAuth("X", self.api_token)
        
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        logger.info(f"ActiveProspectClient initialized with base URL: {self.base_url}")
        logger.info(f"Using API token: {self.api_token[:8]}...")

    async def test_connection(self) -> tuple[bool, str]:
        """Test the API connection"""
        try:
            result = await self.get_events(limit=1)
            if result and 'data' in result:
                return True, "Connection successful"
            else:
                return False, "No data returned from API"        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    async def get_events(self, limit: int = 100, after_id: str = None, before_id: str = None, 
                        start: datetime = None, end: datetime = None, event_type: str = None,
                        rules: str = None, include: list = None, exclude: list = None,
                        sort: str = "desc") -> Dict[str, Any]:
        """Get events from LeadConduit API
        
        Args:
            limit: Maximum number of events to return (1-1000, default 100)
            after_id: Return only events created after this ID (exclusive)
            before_id: Return only events created before this ID (exclusive)
            start: Return only events created at or after this time
            end: Return only events created at or before this time
            event_type: Filter by event type (source, recipient, filter, etc.)
            rules: Stringified array of Rules to select matching events
            include: Array of fields to include (cannot be used with exclude)
            exclude: Array of fields to exclude (cannot be used with include)
            sort: Sort order - 'asc' for oldest first, 'desc' for newest first
        """
        params = {
            "limit": min(limit, 1000),  # API max is 1000
            "sort": sort
        }
        
        if after_id:
            params["after_id"] = after_id
        if before_id:
            params["before_id"] = before_id
        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()
        if event_type:
            params["type"] = event_type
        if rules:
            params["rules"] = rules
        if include:
            params["include"] = include
        if exclude:
            params["exclude"] = exclude
            
        return await self._make_request("events", params)

    async def get_event_by_id(self, event_id: str) -> Dict[str, Any]:
        """Get a specific event by ID"""
        return await self._make_request(f"events/{event_id}")

    async def search_leads(self, query: str = None, sort_by: str = None, sort_dir: str = "desc",
                          from_offset: int = 0, limit: int = 100) -> Dict[str, Any]:
        """Search leads using full text search"""
        params = {
            "from": from_offset,
            "limit": min(limit, 100)  # API max is 100
        }
        
        # The query parameter is required by the API
        if query:
            params["query"] = query
        else:
            params["query"] = "*"  # Default wildcard search
            
        if sort_by:
            params["sort_by"] = sort_by
        if sort_dir:
            params["sort_dir"] = sort_dir
            
        return await self._make_request("search/leads", params)

    async def get_event_statistics(self, start: datetime = None, end: datetime = None,
                                  event_type: str = "source", group_by: str = None,
                                  interval: str = None) -> Dict[str, Any]:
        """Get event statistics"""
        params = {}
        
        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()
        if event_type:
            params["type"] = event_type
        if group_by:
            params["group_by"] = group_by
        if interval:
            params["interval"] = interval
            
        return await self._make_request("events/stats", params)

    async def get_events_export(self, start: datetime = None, end: datetime = None,
                               limit: int = 1000, include_fields: list = None,
                               exclude_fields: list = None) -> Dict[str, Any]:
        """Get events for export using POST endpoint"""
        data = {
            "limit": min(limit, 1000)
        }
        
        if start:
            data["start"] = start.isoformat()
        if end:
            data["end"] = end.isoformat()
        if include_fields:
            data["include"] = include_fields
        if exclude_fields:
            data["exclude"] = exclude_fields
            
        return await self._make_request("events", data, method="POST")

    async def _make_request(self, endpoint: str, params: Dict = None, 
                           method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """Make an HTTP request to the ActiveProspect API"""
        url = f"{self.base_url}/{endpoint}"
        
        logger.info(f"Making {method} request to: {url}")
        logger.info(f"Auth: Basic X:{self.api_token[:8]}...")
        logger.info(f"Params: {params}")
        logger.info(f"Data: {data}")
        
        try:
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                request_kwargs = {
                    'headers': self.headers,
                    'auth': self.auth
                }
                
                if method.upper() == "GET":
                    if params:
                        request_kwargs['params'] = params
                    async with session.get(url, **request_kwargs) as response:
                        return await self._handle_response(response)
                        
                elif method.upper() == "POST":
                    if data:
                        request_kwargs['json'] = data
                    async with session.post(url, **request_kwargs) as response:
                        return await self._handle_response(response)
                        
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {url}")
            raise Exception("Request timeout")
        except Exception as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            raise

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle API response"""
        status = response.status
        response_text = await response.text()
        
        logger.info(f"Response status: {status}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        if status == 200:
            try:
                data = await response.json()
                logger.info(f"Response JSON data received: {len(response_text)} characters")
                
                # Handle different response formats
                if isinstance(data, list):
                    return {"data": data, "count": len(data)}
                else:
                    return data
                    
            except Exception as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.error(f"Response text: {response_text[:500]}...")
                return {"error": "Failed to parse JSON response", "raw_response": response_text}
                
        elif status == 401:
            logger.error("Unauthorized - check API credentials")
            raise Exception("Unauthorized - check API credentials")
        elif status == 429:
            logger.warning("Rate limit exceeded")
            raise Exception("Rate limit exceeded")
        else:
            logger.error(f"API request failed with status {status}: {response_text}")
            raise Exception(f"API request failed with status {status}")
