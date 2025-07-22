"""
Base HubSpot API client
"""
import logging
import json
from django.conf import settings
from ingestion.base.client import BaseAPIClient
from ingestion.base.exceptions import APIException

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
    
    async def make_request(self, method: str, endpoint: str, **kwargs):
        """Override make_request to handle HubSpot-specific errors"""
        try:
            return await super().make_request(method, endpoint, **kwargs)
        except APIException as e:
            # Parse HubSpot-specific error details
            error_str = str(e)
            if "HTTP 400" in error_str:
                try:
                    # Extract JSON error from the error message
                    if '{"status":"error"' in error_str:
                        json_start = error_str.find('{"status":"error"')
                        json_part = error_str[json_start:]
                        error_data = json.loads(json_part)
                        correlation_id = error_data.get('correlationId', 'unknown')
                        logger.error(f"HubSpot API Error - CorrelationId: {correlation_id}, Message: {error_data.get('message', 'Unknown error')}")
                        
                        # Check for specific error types
                        if "after" in error_data.get('message', '').lower():
                            raise APIException(f"Invalid pagination token - CorrelationId: {correlation_id}")
                        elif "properties" in error_data.get('message', '').lower():
                            raise APIException(f"Invalid properties in request - CorrelationId: {correlation_id}")
                        
                except (json.JSONDecodeError, KeyError):
                    pass
            
            # Re-raise the original exception if we can't parse it
            raise e
    
    def get_rate_limit_headers(self) -> dict:
        """Return HubSpot rate limit headers"""
        return {
            'X-HubSpot-RateLimit-Daily': 'X-HubSpot-RateLimit-Daily',
            'X-HubSpot-RateLimit-Daily-Remaining': 'X-HubSpot-RateLimit-Daily-Remaining',
            'X-HubSpot-RateLimit-Secondly': 'X-HubSpot-RateLimit-Secondly',
            'X-HubSpot-RateLimit-Secondly-Remaining': 'X-HubSpot-RateLimit-Secondly-Remaining'
        }
