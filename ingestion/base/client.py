"""
Base API client for all CRM integrations
"""
from abc import ABC, abstractmethod
import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional, List
from ingestion.base.exceptions import APIException, RateLimitException

logger = logging.getLogger(__name__)

class BaseAPIClient(ABC):
    """Base class for all API clients"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = None
        self.headers = {}
        
    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate with the API"""
        pass
        
    @abstractmethod
    def get_rate_limit_headers(self) -> Dict[str, str]:
        """Return rate limit headers for this API"""
        pass
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers=self.headers
        )
        await self.authenticate()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        for attempt in range(3):
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 429:
                        await self.handle_rate_limit(response)
                        continue
                    
                    if response.status >= 400:
                        error_text = await response.text()
                        raise APIException(f"HTTP {response.status}: {error_text}")
                    
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                if attempt == 2:
                    raise APIException(f"Request failed after 3 attempts: {e}")
                await asyncio.sleep(2 ** attempt)
    
    async def handle_rate_limit(self, response: aiohttp.ClientResponse):
        """Handle rate limiting"""
        retry_after = int(response.headers.get('Retry-After', 60))
        logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
        await asyncio.sleep(retry_after)
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
