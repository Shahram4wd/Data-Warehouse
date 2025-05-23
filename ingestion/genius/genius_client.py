# ingestion/genius/genius_client.py
import requests
from .auth import GeniusAuthenticator

class GeniusClient:
    def __init__(self, base_url, username, password):
        self.auth = GeniusAuthenticator(base_url, username, password)
        self.token = self.auth.login()
        self.base_url = base_url.rstrip('/')

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_prospects(self):
        url = f"{self.base_url}/api/prospects/"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()
    
    def get(self, endpoint):
        url = f"{self.base_url.rstrip('/')}{endpoint}"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()

