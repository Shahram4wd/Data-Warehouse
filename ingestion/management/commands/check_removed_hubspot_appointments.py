import logging
from django.core.management.base import BaseCommand
from ingestion.hubspot.hubspot_client import HubspotClient
from django.db import transaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Check for appointments that exist locally but were removed from HubSpot, and remove them locally."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Limit the number of local records to check.")
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
        limit = options["limit"]
        hs_appointment_start_after = options["hs_appointment_start_after"]
        dry_run = options["dry_run"]

        self.stdout.write("Starting check for locally stored appointments that no longer exist in HubSpot...")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No deletions will be performed"))

        # Get local appointments to check
        local_appointments = self._get_local_appointments(hs_appointment_start_after, limit)
        
        if not local_appointments:
            self.stdout.write("No local appointments found to check.")
            return

        # Initialize HubSpot client
        client = HubspotClient()

        # Check which local appointments still exist in HubSpot
        removed_appointments = self._check_appointments_in_hubspot(client, local_appointments)

        # Remove the appointments that no longer exist in HubSpot
        if removed_appointments:
            deleted_count = self._remove_local_appointments(removed_appointments, dry_run)
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"🔍 DRY RUN: Would delete {deleted_count} appointments from local database.")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Deleted {deleted_count} appointments that no longer exist in HubSpot.")
                )
        else:
            self.stdout.write(
                self.style.SUCCESS("✓ All local appointments still exist in HubSpot. No deletions needed.")
            )

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
        """Check which local appointments no longer exist in HubSpot."""
        import asyncio
        
        self.stdout.write(f"Checking {len(local_appointments)} appointments in HubSpot...")
        
        local_ids = [apt['id'] for apt in local_appointments]
        
        async def check_hubspot_existence():
            # Check appointments in batches to avoid overwhelming the API
            batch_size = 100
            missing_appointments = []
            
            for i in range(0, len(local_ids), batch_size):
                batch_ids = local_ids[i:i + batch_size]
                self.stdout.write(f"Checking batch {i//batch_size + 1}: {len(batch_ids)} appointments...")
                
                # Try to fetch these appointments from HubSpot
                existing_in_hubspot = await self._check_hubspot_batch(client, batch_ids)
                
                # Find which ones are missing
                existing_ids = set(existing_in_hubspot)
                missing_ids = set(batch_ids) - existing_ids
                
                # Get the full local appointment data for missing ones
                missing_in_batch = [apt for apt in local_appointments if apt['id'] in missing_ids]
                missing_appointments.extend(missing_in_batch)
                
                self.stdout.write(f"Batch {i//batch_size + 1}: {len(missing_in_batch)} appointments not found in HubSpot")
            
            return missing_appointments
        
        return asyncio.run(check_hubspot_existence())

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
