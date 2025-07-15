
from ingestion.models.hubspot import Hubspot_Appointment
from django.db import transaction
from asgiref.sync import sync_to_async
from ingestion.sync.hubspot.engines.base import HubSpotBaseSyncEngine

class HubSpotAppointmentsRemovalSyncEngine(HubSpotBaseSyncEngine):
    async def fetch_data(self, **kwargs):
        return

    async def transform_data(self, raw_data):
        return raw_data

    async def validate_data(self, data):
        return data

    async def save_data(self, validated_data):
        return {'created': 0, 'updated': 0, 'failed': 0}

    def __init__(self, **kwargs):
        super().__init__('appointments_removal', **kwargs)

    async def get_local_appointments(self, start_after=None, limit=None):
        from datetime import datetime, timezone
        def _query():
            queryset = Hubspot_Appointment.objects.all()
            if start_after:
                try:
                    start_date = datetime.strptime(start_after, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    queryset = queryset.filter(hs_appointment_start__gte=start_date)
                except ValueError:
                    return []
            if limit:
                queryset = queryset[:limit]
            return list(queryset.values('id', 'hs_appointment_start', 'hs_appointment_name'))
        return await sync_to_async(_query, thread_sensitive=True)()

    async def remove_local_appointments(self, appointments_to_remove, dry_run=False):
        import logging
        logger = logging.getLogger("hubspot.appointments_removal")
        if not appointments_to_remove:
            return 0
        ids_to_remove = [apt['id'] for apt in appointments_to_remove]
        logger.info(f"Deleting HubSpot appointments (IDs): {ids_to_remove}")
        print(f"Deleting HubSpot appointments (IDs): {ids_to_remove}")
        if not dry_run:
            def _delete():
                with transaction.atomic():
                    deleted_count = Hubspot_Appointment.objects.filter(id__in=ids_to_remove).delete()[0]
                    return deleted_count
            return await sync_to_async(_delete, thread_sensitive=True)()
        else:
            return len(appointments_to_remove)

    async def run_removal(self, limit=None, start_after=None, dry_run=False, stdout=None):
        from ingestion.sync.hubspot.clients.appointments_removal import HubSpotAppointmentsRemovalClient
        from django.conf import settings
        if stdout:
            stdout.write("Starting check for locally stored appointments that no longer exist in HubSpot...")
            if dry_run:
                stdout.write("🔍 DRY RUN MODE - No deletions will be performed")

        # Step 1: Fetch local appointments (async)
        local_appointments = await self.get_local_appointments(start_after, limit)
        if not local_appointments:
            if stdout:
                stdout.write("No local appointments found to check.")
            return

        # Step 2: Check which local appointments are missing in HubSpot
        api_token = settings.HUBSPOT_API_TOKEN
        client = HubSpotAppointmentsRemovalClient(api_token=api_token)
        removed_appointments = await client._get_missing_appointments_async(local_appointments, batch_size=100, stdout=stdout)

        # Step 3: Remove missing appointments (or dry-run)
        if removed_appointments:
            deleted_count = await self.remove_local_appointments(removed_appointments, dry_run)
            if dry_run:
                if stdout:
                    stdout.write(f"🔍 DRY RUN: Would delete {deleted_count} appointments from local database.")
            else:
                if stdout:
                    stdout.write(f"✓ Deleted {deleted_count} appointments that no longer exist in HubSpot.")
        else:
            if stdout:
                stdout.write("✓ All local appointments still exist in HubSpot. No deletions needed.")
