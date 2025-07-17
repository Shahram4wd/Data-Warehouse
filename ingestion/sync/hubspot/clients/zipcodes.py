"""
HubSpot zipcode client for fetching CSV data from GitHub
"""
import requests
from ingestion.sync.hubspot.clients.zipcode_client import HubSpotZipCodeClient as BaseZipCodeClient

class HubSpotZipCodeClient(BaseZipCodeClient):
    """Client for fetching zipcode data from GitHub CSV"""
    
    def __init__(self):
        super().__init__()
    
    def fetch_csv(self):
        """Fetch CSV content from GitHub - delegates to base client"""
        return super().fetch_csv()
