
import aiohttp
from .base import HubSpotBaseClient

class HubSpotAppointmentsRemovalClient(HubSpotBaseClient):
    def __init__(self, api_token=None):
        super().__init__(api_token=api_token)

    async def batch_check_appointments(self, appointment_ids):
        await self.authenticate()
        import logging
        logger = logging.getLogger("hubspot.appointments_removal.client")
        url = f"{self.base_url}/crm/v3/objects/0-421/batch/read"
        payload = {
            "inputs": [{"id": str(apt_id)} for apt_id in appointment_ids],
            "properties": ["hs_object_id"]
        }
        logger.debug(f"Sending batch_check_appointments payload: {payload}")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=payload, timeout=60) as response:
                logger.debug(f"HubSpot batch_check_appointments response status: {response.status}")
                raw = await response.text()
                logger.debug(f"HubSpot batch_check_appointments raw response: {raw}")
                if response.status == 200:
                    data = await response.json()
                    return [result.get("id") for result in data.get("results", [])]
                return []

    async def check_individual_appointments(self, appointment_ids):
        await self.authenticate()
        existing_ids = []
        async with aiohttp.ClientSession() as session:
            for apt_id in appointment_ids:
                url = f"{self.base_url}/crm/v3/objects/0-421/{apt_id}"
                async with session.get(url, headers=self.headers, timeout=30) as response:
                    if response.status == 200:
                        existing_ids.append(apt_id)
        return existing_ids

    async def _get_missing_appointments_async(self, local_appointments, batch_size=100, stdout=None):
        local_ids = [apt['id'] for apt in local_appointments]
        missing_appointments = []
        for i in range(0, len(local_ids), batch_size):
            batch_ids = local_ids[i:i + batch_size]
            if stdout:
                stdout.write(f"Checking batch {i//batch_size + 1}: {len(batch_ids)} appointments...")
            try:
                existing_in_hubspot = await self.batch_check_appointments(batch_ids)
            except Exception:
                existing_in_hubspot = await self.check_individual_appointments(batch_ids)
            existing_ids = set(existing_in_hubspot)
            missing_ids = set(batch_ids) - existing_ids
            missing_in_batch = [apt for apt in local_appointments if apt['id'] in missing_ids]
            missing_appointments.extend(missing_in_batch)
            if stdout:
                stdout.write(f"Batch {i//batch_size + 1}: {len(missing_in_batch)} appointments not found in HubSpot")
        return missing_appointments

    def get_missing_appointments(self, local_appointments, batch_size=100, stdout=None):
        import asyncio
        return asyncio.run(self._get_missing_appointments_async(local_appointments, batch_size, stdout))
