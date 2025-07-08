"""
Base HubSpot API client
"""
import logging
from django.conf import settings
from ingestion.base.client import BaseAPIClient

logger = logging.getLogger(__name__)

class HubSpotBaseClient(BaseAPIClient):
    """Base HubSpot API client with common functionality"""
    
    def __init__(self, api_token=None):
        super().__init__(base_url="https://api.hubapi.com", timeout=60)
        self.api_token = api_token or settings.HUBSPOT_API_TOKEN
        
    async def authenticate(self) -> None:
        """Set up authentication headers"""
        self.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        })
        logger.info(f"HubSpot client initialized with token: {self.api_token[:5]}...{self.api_token[-5:]}")
    
    def get_rate_limit_headers(self) -> dict:
        """Return HubSpot rate limit headers"""
        return {
            'X-HubSpot-RateLimit-Daily': 'X-HubSpot-RateLimit-Daily',
            'X-HubSpot-RateLimit-Daily-Remaining': 'X-HubSpot-RateLimit-Daily-Remaining',
            'X-HubSpot-RateLimit-Secondly': 'X-HubSpot-RateLimit-Secondly',
            'X-HubSpot-RateLimit-Secondly-Remaining': 'X-HubSpot-RateLimit-Secondly-Remaining'
        }
