"""
Engine for checking and removing HubSpot contacts that no longer exist remotely
Follows import_refactoring.md enterprise architecture standards
"""
from django.db import transaction
from asgiref.sync import sync_to_async
from ingestion.models.hubspot import Hubspot_Contact
from ingestion.sync.hubspot.engines.base import HubSpotBaseSyncEngine

class HubSpotContactsRemovalSyncEngine(HubSpotBaseSyncEngine):
    # Required abstract methods for BaseSyncEngine (not used in removal, but must be implemented)
    async def fetch_data(self, **kwargs):
        return

    async def transform_data(self, raw_data):
        return raw_data

    async def validate_data(self, data):
        return data

    async def save_data(self, validated_data):
        return {'created': 0, 'updated': 0, 'failed': 0}
    async def run_removal(self, limit=None, created_after=None, dry_run=False, stdout=None):
        """Async orchestration for removal of local contacts not in HubSpot"""
        from ingestion.sync.hubspot.clients.contacts_removal import HubSpotContactsRemovalClient
        from django.conf import settings
        import math

        if stdout:
            stdout.write("Starting check for locally stored contacts that no longer exist in HubSpot...")
            if dry_run:
                stdout.write("🔍 DRY RUN MODE - No deletions will be performed")

        # Step 1: Fetch local contacts (async)
        local_contacts = await self.get_local_contacts(created_after, limit)
        if not local_contacts:
            if stdout:
                stdout.write("No local contacts found to check.")
            return

        # Step 2: Check which local contacts are missing in HubSpot
        api_token = settings.HUBSPOT_API_TOKEN
        client = HubSpotContactsRemovalClient(api_token=api_token)
        # Use async version of get_missing_contacts
        removed_contacts = await client._get_missing_contacts_async(local_contacts, batch_size=self.batch_size, stdout=stdout)

        # Step 3: Remove missing contacts (or dry-run)
        if removed_contacts:
            deleted_count = await self.remove_local_contacts(removed_contacts, dry_run)
            if dry_run:
                if stdout:
                    stdout.write(f"🔍 DRY RUN: Would delete {deleted_count} contacts from local database.")
            else:
                if stdout:
                    stdout.write(f"✓ Deleted {deleted_count} contacts that no longer exist in HubSpot.")
        else:
            if stdout:
                stdout.write("✓ All local contacts still exist in HubSpot. No deletions needed.")
    """Sync engine for removing HubSpot contacts"""
    def __init__(self, **kwargs):
        super().__init__('contacts_removal', **kwargs)

    async def get_local_contacts(self, created_after=None, limit=None):
        from datetime import datetime, timezone
        def _query():
            queryset = Hubspot_Contact.objects.all()
            if created_after:
                created_date = datetime.strptime(created_after, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                queryset = queryset.filter(createdate__gte=created_date)
            if limit:
                queryset = queryset[:limit]
            return list(queryset.values('id', 'createdate', 'firstname', 'lastname', 'email'))
        return await sync_to_async(_query, thread_sensitive=True)()

    async def remove_local_contacts(self, contacts_to_remove, dry_run=False):
        import logging
        logger = logging.getLogger("hubspot.contacts_removal")
        if not contacts_to_remove:
            return 0
        ids_to_remove = [contact['id'] for contact in contacts_to_remove]
        # Log to file
        logger.info(f"Deleting HubSpot contacts (IDs): {ids_to_remove}")
        # Print to console
        print(f"Deleting HubSpot contacts (IDs): {ids_to_remove}")
        if not dry_run:
            def _delete():
                with transaction.atomic():
                    deleted_count = Hubspot_Contact.objects.filter(id__in=ids_to_remove).delete()[0]
                    return deleted_count
            return await sync_to_async(_delete, thread_sensitive=True)()
        else:
            return len(contacts_to_remove)
