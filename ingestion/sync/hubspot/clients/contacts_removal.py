"""
Client for checking existence of HubSpot contacts (removed contacts logic)
Follows import_refactoring.md enterprise architecture standards
"""
import aiohttp
from .base import HubSpotBaseClient

class HubSpotContactsRemovalClient(HubSpotBaseClient):
    def __init__(self, api_token=None):
        super().__init__(api_token=api_token)


    async def batch_check_contacts(self, contact_ids):
        await self.authenticate()
        import logging
        logger = logging.getLogger("hubspot.contacts_removal.client")
        url = f"{self.base_url}/crm/v3/objects/contacts/batch/read"
        payload = {
            "inputs": [{"id": str(contact_id)} for contact_id in contact_ids],
            "properties": ["hs_object_id"]
        }
        logger.debug(f"Sending batch_check_contacts payload: {payload}")
        # print(f"[DEBUG] Sending batch_check_contacts payload: {payload}")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=payload, timeout=60) as response:
                logger.debug(f"HubSpot batch_check_contacts response status: {response.status}")
                raw = await response.text()
                # print(f"[DEBUG] HubSpot batch_check_contacts response status: {response.status}")
                # print(f"[DEBUG] HubSpot batch_check_contacts raw response: {raw}")
                logger.debug(f"HubSpot batch_check_contacts raw response: {raw}")
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])
                    return [result.get("id") for result in results]
                return []

    async def check_individual_contacts(self, contact_ids):
        await self.authenticate()
        existing_ids = []
        async with aiohttp.ClientSession() as session:
            for contact_id in contact_ids:
                url = f"{self.base_url}/crm/v3/objects/contacts/{contact_id}"
                async with session.get(url, headers=self.headers, timeout=30) as response:
                    if response.status == 200:
                        existing_ids.append(contact_id)
        return existing_ids

    async def _get_missing_contacts_async(self, local_contacts, batch_size=100, stdout=None):
        local_ids = [contact['id'] for contact in local_contacts]
        missing_contacts = []
        for i in range(0, len(local_ids), batch_size):
            batch_ids = local_ids[i:i + batch_size]
            if stdout:
                stdout.write(f"Checking batch {i//batch_size + 1}: {len(batch_ids)} contacts...")
            try:
                existing_in_hubspot = await self.batch_check_contacts(batch_ids)
            except Exception:
                existing_in_hubspot = await self.check_individual_contacts(batch_ids)
            existing_ids = set(existing_in_hubspot)
            missing_ids = set(batch_ids) - existing_ids
            missing_in_batch = [contact for contact in local_contacts if contact['id'] in missing_ids]
            missing_contacts.extend(missing_in_batch)
            if stdout:
                stdout.write(f"Batch {i//batch_size + 1}: {len(missing_in_batch)} contacts not found in HubSpot")
        return missing_contacts

    def get_missing_contacts(self, local_contacts, batch_size=100, stdout=None):
        import asyncio
        return asyncio.run(self._get_missing_contacts_async(local_contacts, batch_size, stdout))
