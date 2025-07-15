"""
Engine for syncing HubSpot Genius Users
Follows import_refactoring.md enterprise architecture standards
"""
import asyncio
from asgiref.sync import sync_to_async
from ingestion.models.hubspot import Hubspot_GeniusUser
from ..clients.genius_users_client import HubSpotGeniusUsersClient
from ..processors.genius_users_processor import HubSpotGeniusUsersProcessor
from .base import HubSpotBaseSyncEngine

class HubSpotGeniusUsersSyncEngine(HubSpotBaseSyncEngine):
    def __init__(self, api_token=None, batch_size=100, dry_run=False, stdout=None, max_records=0, full=False):
        super().__init__('genius_users', batch_size=batch_size, dry_run=dry_run)
        self.api_token = api_token
        self.client = HubSpotGeniusUsersClient(api_token=api_token)
        self.processor = HubSpotGeniusUsersProcessor()
        self.stdout = stdout
        self.max_records = max_records
        self.full = full

    async def initialize_client(self):
        pass

    def get_default_batch_size(self) -> int:
        return 100

    async def fetch_data(self, **kwargs):
        return

    async def transform_data(self, raw_data):
        return raw_data

    async def validate_data(self, data):
        return data

    async def save_data(self, validated_data):
        return {'created': 0, 'updated': 0, 'failed': 0}

    async def cleanup(self):
        pass

    async def run_sync(self):
        total = 0
        processed_count = 0
        # List of properties to fetch from HubSpot API
        properties = [
            "hs_object_id", "hs_createdate", "hs_lastmodifieddate", "createdAt", "updatedAt", "archived",
            "arrivy_user_id", "division", "division_id", "email", "job_title", "name", "title_id",
            "user_account_type", "user_id", "user_status_inactive"
        ]
        async for batch in self.client.fetch_all_users(batch_size=self.batch_size, stdout=self.stdout, properties=properties):
            if self.max_records and (processed_count + len(batch)) > self.max_records:
                batch = batch[:self.max_records - processed_count]
            processed = [self.processor.process(user) for user in batch]
            if not self.dry_run:
                await self.bulk_upsert(processed)
            total += len(processed)
            processed_count += len(batch)
            if self.stdout:
                self.stdout.write(f"Processed {total} genius users...")
            if self.max_records and processed_count >= self.max_records:
                break
        if self.stdout:
            self.stdout.write(f"Sync complete. Total genius users processed: {total}")

    @sync_to_async
    def bulk_upsert(self, records):
        # Upsert by id (primary key)
        objs = [Hubspot_GeniusUser(**rec) for rec in records]
        Hubspot_GeniusUser.objects.bulk_create(
            objs,
            update_conflicts=True,
            update_fields=[
                "hs_object_id", "hs_createdate", "hs_lastmodifieddate", "archived",
                "arrivy_user_id", "division", "division_id", "email", "job_title", "name", "title_id",
                "user_account_type", "user_id", "user_status_inactive", "updated_at"
            ],
            unique_fields=["id"]
        )
