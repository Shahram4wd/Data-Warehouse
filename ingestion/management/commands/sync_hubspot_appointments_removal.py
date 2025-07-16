

import logging
from django.core.management.base import BaseCommand
from ingestion.sync.hubspot.engines.appointments_removal import HubSpotAppointmentsRemovalSyncEngine
import asyncio

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Check for appointments that exist locally but were removed from HubSpot, and remove them locally."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Limit the number of local records to check.")
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Batch size for processing records.",
        )
        parser.add_argument(
            "--hs_appointment_start_after",
            type=str,
            default=None,
            help="Only check local appointments with start dates after this date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Only show what would be removed without actually deleting.",
        )

    def handle(self, *args, **options):
        asyncio.run(self.async_handle(**options))

    async def async_handle(self, **options):
        limit = options["limit"]
        hs_appointment_start_after = options["hs_appointment_start_after"]
        dry_run = options["dry_run"]

        engine = HubSpotAppointmentsRemovalSyncEngine(
            batch_size=options.get('batch_size', 100),
            dry_run=dry_run
        )
        await engine.run_removal(
            limit=limit,
            start_after=hs_appointment_start_after,
            dry_run=dry_run,
            stdout=self.stdout
        )

    def _check_appointments_in_hubspot(self, client, local_appointments):
        self.stdout.write(f"Checking {len(local_appointments)} appointments in HubSpot...")
        local_ids = [apt['id'] for apt in local_appointments]
        batch_size = 100
        missing_appointments = []

        async def check_hubspot_existence():
            for i in range(0, len(local_ids), batch_size):
                batch_ids = local_ids[i:i + batch_size]
                self.stdout.write(f"Checking batch {i//batch_size + 1}: {len(batch_ids)} appointments...")
                try:
                    existing_in_hubspot = await client.batch_check_appointments(batch_ids)
                except Exception:
                    existing_in_hubspot = await client.check_individual_appointments(batch_ids)
                existing_ids = set(existing_in_hubspot)
                missing_ids = set(batch_ids) - existing_ids
                missing_in_batch = [apt for apt in local_appointments if apt['id'] in missing_ids]
                missing_appointments.extend(missing_in_batch)
                self.stdout.write(f"Batch {i//batch_size + 1}: {len(missing_in_batch)} appointments not found in HubSpot")
            return missing_appointments

        return asyncio.run(check_hubspot_existence())

    def _get_local_appointments(self, start_after, limit):
        """Get appointments from local database to check against HubSpot."""
        from ingestion.models.hubspot import Hubspot_Appointment
        from datetime import datetime, timezone
        
        self.stdout.write("Fetching local appointments...")
        
        # Build query
        queryset = Hubspot_Appointment.objects.all()
        
        # Apply date filter if provided
        if start_after:
            try:
                start_date = datetime.strptime(start_after, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                queryset = queryset.filter(hs_appointment_start__gte=start_date)
                self.stdout.write(f"Filtering by appointments starting after {start_after}")
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Invalid date format: {start_after}. Use YYYY-MM-DD."))
                return []
        
        # Apply limit
        if limit:
            queryset = queryset[:limit]
            
        # Get the appointments
        appointments = list(queryset.values('id', 'hs_appointment_start', 'hs_appointment_name'))
        
        self.stdout.write(f"Found {len(appointments)} local appointments to check")
        return appointments

    def _check_appointments_in_hubspot(self, client, local_appointments):
        """Check which local appointments no longer exist in HubSpot, only after confirming with individual 404."""
        import asyncio
        self.stdout.write(f"Checking {len(local_appointments)} appointments in HubSpot...")
        local_ids = [apt['id'] for apt in local_appointments]
        batch_size = 100
        truly_missing_appointments = []

        async def check_hubspot_existence():
            for i in range(0, len(local_ids), batch_size):
                batch_ids = local_ids[i:i + batch_size]
                self.stdout.write(f"Checking batch {i//batch_size + 1}: {len(batch_ids)} appointments...")
                # Try to fetch these appointments from HubSpot (batch)
                existing_in_hubspot = await self._check_hubspot_batch(client, batch_ids)
                existing_ids = set(existing_in_hubspot)
                missing_ids = set(batch_ids) - existing_ids
                self.stdout.write(f"Batch {i//batch_size + 1}: {len(missing_ids)} appointments not found in batch API, confirming individually...")
                # Confirm missing ones with individual check (must get 404)
                if missing_ids:
                    confirmed_missing = await self._confirm_missing_with_individual(client, list(missing_ids))
                    truly_missing_appointments.extend([apt for apt in local_appointments if apt['id'] in confirmed_missing])
                    self.stdout.write(f"Batch {i//batch_size + 1}: {len(confirmed_missing)} appointments confirmed missing after 404 check.")
            return truly_missing_appointments

        return asyncio.run(check_hubspot_existence())

    async def _confirm_missing_with_individual(self, client, appointment_ids):
        """Return only those IDs that are confirmed missing by a 404 from HubSpot."""
        import aiohttp
        confirmed_missing = []
        async with aiohttp.ClientSession() as session:
            for apt_id in appointment_ids:
                try:
                    url = f"{client.BASE_URL}/crm/v3/objects/0-421/{apt_id}"
                    async with session.get(url, headers=client.headers, timeout=30) as response:
                        if response.status == 404:
                            confirmed_missing.append(apt_id)
                        elif response.status == 200:
                            continue  # Exists
                        else:
                            self.stdout.write(f"Warning: Unexpected status {response.status} for appointment {apt_id}, skipping removal.")
                except Exception as e:
                    self.stdout.write(f"Error checking appointment {apt_id}: {str(e)}. Skipping removal.")
        return confirmed_missing

    async def _check_hubspot_batch(self, client, appointment_ids):
        """Check a batch of appointment IDs in HubSpot and return which ones exist."""
        # Use HubSpot's batch read API to efficiently check multiple appointments
        url = f"{client.BASE_URL}/crm/v3/objects/0-421/batch/read"
        
        payload = {
            "inputs": [{"id": apt_id} for apt_id in appointment_ids],
            "properties": ["hs_object_id"]  # Minimal properties to reduce response size
        }
        
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=client.headers, json=payload, timeout=60) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        # Return the IDs that exist in HubSpot
                        return [result["id"] for result in results]
                    else:
                        # If batch API fails, fall back to individual checks
                        self.stdout.write(f"Batch API returned status {response.status}, falling back to individual checks")
                        return await self._check_individual_appointments(client, appointment_ids)
                        
            except Exception as e:
                self.stdout.write(f"Error in batch check: {str(e)}, falling back to individual checks")
                return await self._check_individual_appointments(client, appointment_ids)

    async def _check_individual_appointments(self, client, appointment_ids):
        """Fallback method to check appointments individually."""
        existing_ids = []
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            for apt_id in appointment_ids:
                try:
                    url = f"{client.BASE_URL}/crm/v3/objects/0-421/{apt_id}"
                    async with session.get(url, headers=client.headers, timeout=30) as response:
                        if response.status == 200:
                            existing_ids.append(apt_id)
                        # 404 means the appointment doesn't exist in HubSpot
                except Exception:
                    # If we can't check, assume it exists to be safe
                    existing_ids.append(apt_id)
                    
        return existing_ids

    def _remove_local_appointments(self, appointments_to_remove, dry_run=False):
        """Remove appointments from local database."""
        from ingestion.models.hubspot import Hubspot_Appointment
        
        if not appointments_to_remove:
            return 0
            
        ids_to_remove = [apt['id'] for apt in appointments_to_remove]
        
        self.stdout.write(f"Appointments to remove:")
        for apt in appointments_to_remove[:10]:  # Show first 10
            name = apt.get('hs_appointment_name', 'Unnamed')
            start = apt.get('hs_appointment_start', 'No date')
            self.stdout.write(f"  - ID: {apt['id']}, Name: {name}, Start: {start}")
        
        if len(appointments_to_remove) > 10:
            self.stdout.write(f"  ... and {len(appointments_to_remove) - 10} more")
        
        if not dry_run:
            with transaction.atomic():
                deleted_count = Hubspot_Appointment.objects.filter(id__in=ids_to_remove).delete()[0]
                self.stdout.write(f"Deleted {deleted_count} appointments from local database")
                return deleted_count
        else:
            return len(appointments_to_remove)
