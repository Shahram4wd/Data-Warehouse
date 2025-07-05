import logging
from django.core.management.base import BaseCommand
from ingestion.hubspot.hubspot_client import HubspotClient
from django.db import transaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Check for contacts that exist locally but were removed from HubSpot, and remove them locally."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Limit the number of local records to check.")
        parser.add_argument(
            "--hs_contact_created_after",
            type=str,
            default=None,
            help="Only check local contacts created after this date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Only show what would be removed without actually deleting.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        hs_contact_created_after = options["hs_contact_created_after"]
        dry_run = options["dry_run"]

        self.stdout.write("Starting check for locally stored contacts that no longer exist in HubSpot...")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No deletions will be performed"))

        # Get local contacts to check
        local_contacts = self._get_local_contacts(hs_contact_created_after, limit)
        
        if not local_contacts:
            self.stdout.write("No local contacts found to check.")
            return

        # Initialize HubSpot client
        client = HubspotClient()

        # Check which local contacts still exist in HubSpot
        removed_contacts = self._check_contacts_in_hubspot(client, local_contacts)

        # Remove the contacts that no longer exist in HubSpot
        if removed_contacts:
            deleted_count = self._remove_local_contacts(removed_contacts, dry_run)
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"🔍 DRY RUN: Would delete {deleted_count} contacts from local database.")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Deleted {deleted_count} contacts that no longer exist in HubSpot.")
                )
        else:
            self.stdout.write(
                self.style.SUCCESS("✓ All local contacts still exist in HubSpot. No deletions needed.")
            )

    def _get_local_contacts(self, created_after, limit):
        """Get contacts from local database to check against HubSpot."""
        from ingestion.models.hubspot import Hubspot_Contact
        from datetime import datetime, timezone
        
        self.stdout.write("Fetching local contacts...")
        
        # Build query
        queryset = Hubspot_Contact.objects.all()
        
        # Apply date filter if provided
        if created_after:
            try:
                created_date = datetime.strptime(created_after, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                queryset = queryset.filter(createdate__gte=created_date)
                self.stdout.write(f"Filtering by contacts created after {created_after}")
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Invalid date format: {created_after}. Use YYYY-MM-DD."))
                return []
        
        # Apply limit
        if limit:
            queryset = queryset[:limit]
            
        # Get the contacts
        contacts = list(queryset.values('id', 'createdate', 'firstname', 'lastname', 'email'))
        
        self.stdout.write(f"Found {len(contacts)} local contacts to check")
        return contacts

    def _check_contacts_in_hubspot(self, client, local_contacts):
        """Check which local contacts no longer exist in HubSpot."""
        import asyncio
        
        self.stdout.write(f"Checking {len(local_contacts)} contacts in HubSpot...")
        
        local_ids = [contact['id'] for contact in local_contacts]
        
        async def check_hubspot_existence():
            # Check contacts in batches to avoid overwhelming the API
            batch_size = 100
            missing_contacts = []
            
            for i in range(0, len(local_ids), batch_size):
                batch_ids = local_ids[i:i + batch_size]
                self.stdout.write(f"Checking batch {i//batch_size + 1}: {len(batch_ids)} contacts...")
                
                # Try to fetch these contacts from HubSpot
                existing_in_hubspot = await self._check_hubspot_batch(client, batch_ids)
                
                # Find which ones are missing
                existing_ids = set(existing_in_hubspot)
                missing_ids = set(batch_ids) - existing_ids
                
                # Get the full local contact data for missing ones
                missing_in_batch = [contact for contact in local_contacts if contact['id'] in missing_ids]
                missing_contacts.extend(missing_in_batch)
                
                self.stdout.write(f"Batch {i//batch_size + 1}: {len(missing_in_batch)} contacts not found in HubSpot")
            
            return missing_contacts
        
        return asyncio.run(check_hubspot_existence())

    async def _check_hubspot_batch(self, client, contact_ids):
        """Check a batch of contact IDs in HubSpot and return which ones exist."""
        # Use HubSpot's batch read API to efficiently check multiple contacts
        url = f"{client.BASE_URL}/crm/v3/objects/contacts/batch/read"
        
        payload = {
            "inputs": [{"id": contact_id} for contact_id in contact_ids],
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
                        return await self._check_individual_contacts(client, contact_ids)
                        
            except Exception as e:
                self.stdout.write(f"Error in batch check: {str(e)}, falling back to individual checks")
                return await self._check_individual_contacts(client, contact_ids)

    async def _check_individual_contacts(self, client, contact_ids):
        """Fallback method to check contacts individually."""
        existing_ids = []
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            for contact_id in contact_ids:
                try:
                    url = f"{client.BASE_URL}/crm/v3/objects/contacts/{contact_id}"
                    async with session.get(url, headers=client.headers, timeout=30) as response:
                        if response.status == 200:
                            existing_ids.append(contact_id)
                        # 404 means the contact doesn't exist in HubSpot
                except Exception:
                    # If we can't check, assume it exists to be safe
                    existing_ids.append(contact_id)
                    
        return existing_ids

    def _remove_local_contacts(self, contacts_to_remove, dry_run=False):
        """Remove contacts from local database."""
        from ingestion.models.hubspot import Hubspot_Contact
        
        if not contacts_to_remove:
            return 0
            
        ids_to_remove = [contact['id'] for contact in contacts_to_remove]
        
        self.stdout.write(f"Contacts to remove:")
        for contact in contacts_to_remove[:10]:  # Show first 10
            firstname = contact.get('firstname', '')
            lastname = contact.get('lastname', '')
            email = contact.get('email', 'No email')
            name = f"{firstname} {lastname}".strip() or 'Unnamed'
            created = contact.get('createdate', 'No date')
            self.stdout.write(f"  - ID: {contact['id']}, Name: {name}, Email: {email}, Created: {created}")
        
        if len(contacts_to_remove) > 10:
            self.stdout.write(f"  ... and {len(contacts_to_remove) - 10} more")
        
        if not dry_run:
            with transaction.atomic():
                deleted_count = Hubspot_Contact.objects.filter(id__in=ids_to_remove).delete()[0]
                self.stdout.write(f"Deleted {deleted_count} contacts from local database")
                return deleted_count
        else:
            return len(contacts_to_remove)