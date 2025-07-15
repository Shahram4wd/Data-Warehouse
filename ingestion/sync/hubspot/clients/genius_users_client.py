"""
Client for fetching Genius Users from HubSpot (custom object 2-42119425)
Follows import_refactoring.md enterprise architecture standards
"""
import aiohttp
from .base import HubSpotBaseClient

class HubSpotGeniusUsersClient(HubSpotBaseClient):
    def __init__(self, api_token=None):
        super().__init__(api_token=api_token)
        self.object_type = "2-42119425"

    async def fetch_users_batch(self, limit=100, after=None, properties=None):
        await self.authenticate()
        url = f"{self.base_url}/crm/v3/objects/{self.object_type}/"
        params = {"limit": limit}
        if after:
            params["after"] = after
        if properties:
            # HubSpot API expects comma-separated list for properties
            params["properties"] = ",".join(properties)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raw = await response.text()
                    raise Exception(f"HubSpot API error {response.status}: {raw}")

    async def fetch_all_users(self, batch_size=100, stdout=None, properties=None):
        """Async generator to fetch all Genius Users in batches"""
        after = None
        while True:
            data = await self.fetch_users_batch(limit=batch_size, after=after, properties=properties)
            results = data.get("results", [])
            if not results:
                break
            yield results
            paging = data.get("paging", {})
            next_page = paging.get("next", {})
            after = next_page.get("after")
            if not after:
                break
