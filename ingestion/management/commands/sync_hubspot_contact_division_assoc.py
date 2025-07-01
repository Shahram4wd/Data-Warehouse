import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Tuple
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from asgiref.sync import sync_to_async

from ingestion.hubspot.hubspot_client import HubspotClient
from ingestion.models.hubspot import (
    Hubspot_ContactDivisionAssociation,
    Hubspot_Contact,
    Hubspot_Division,
    Hubspot_SyncHistory
)

logger = logging.getLogger(__name__)

# Mapping association types to HubSpot object types
ASSOCATION_MAPPING = {
    'division_to_contact': {
        'from_object': '2-37778609',  # custom division object type
        'to_object': 'contacts'       # contact object type
    },
    'contact_to_company': {
        'from_object': 'contacts',    # contact object type
        'to_object': 'companies'      # company object type
    }
}

class Command(BaseCommand):
    help = 'Sync HubSpot contact to division associations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of contacts to process for testing (default: process all)'
        )
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform a full sync instead of incremental'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Show debug output'
        )
        parser.add_argument(
            '--lastmodifieddate',
            type=str,
            help='Filter associations modified after this date (YYYY-MM-DD format)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting HubSpot contact-division associations sync..."))
        
        # Run the async sync
        try:
            asyncio.run(self.sync_associations(options))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Sync failed: {str(e)}'))
            logger.error(f"HubSpot contact-division associations sync failed: {str(e)}")

    async def sync_associations(self, options):
        """Main sync logic with adaptive chunking"""
        from_object = ASSOCATION_MAPPING['division_to_contact']['from_object']
        to_object = ASSOCATION_MAPPING['division_to_contact']['to_object']
        
        full_sync = options.get("full")
        lastmodifieddate = options.get("lastmodifieddate")
        limit = options.get('limit')
        
        # Get the last sync time
        endpoint = "associations_contact_to_division"
        
        # Priority: 1) --lastmodifieddate parameter, 2) database last sync, 3) full sync
        if lastmodifieddate:
            try:
                last_sync = datetime.strptime(lastmodifieddate, "%Y-%m-%d")
                last_sync = timezone.make_aware(last_sync)
                self.stdout.write(f"Using provided lastmodifieddate filter: {lastmodifieddate}")
            except ValueError:
                raise CommandError(f"Invalid date format for --lastmodifieddate. Use YYYY-MM-DD format.")
        elif full_sync:
            last_sync = None
        else:
            last_sync = await self._get_last_sync_async(endpoint)
        
        if last_sync:
            self.stdout.write(f"Performing delta sync since {last_sync}")
        else:
            self.stdout.write("Performing full sync")
        
        # Initialize client
        client = HubspotClient()
        
        if limit:
            self.stdout.write(f"Limited mode: will process up to {limit} associations for testing")
        else:
            self.stdout.write(f"Full sync mode: downloading all division_to_contact associations from HubSpot")

        try:
            # Get association labels first
            self.stdout.write(f"Fetching association labels between {from_object} and {to_object}...")
            labels = await client.get_association_labels(
                from_object_type=from_object,
                to_object_type=to_object
            )
            
            if not labels:
                self.stdout.write(self.style.WARNING("No association labels found between these object types"))
                return
            
            self.stdout.write(f"Found {len(labels)} association labels:")
            for label in labels:
                label_name = label.get('label', 'Unknown')
                label_type = label.get('typeId', 'Unknown')
                self.stdout.write(f"  - {label_name} (Type ID: {label_type})")
            
            # Get all division IDs from our local database
            self.stdout.write(f"Getting division IDs from local database...")
            division_ids = await self._get_division_ids_async()
            
            if not division_ids:
                self.stdout.write(self.style.WARNING("No divisions found in local database. Please sync divisions first."))
                return
            
            self.stdout.write(f"Found {len(division_ids)} divisions to check for contact associations")
            
            # Use adaptive chunking to fetch associations
            all_associations = await self._fetch_associations_adaptive(
                client, from_object, to_object, division_ids, last_sync, timezone.now(), limit
            )
            
            # Process all fetched associations
            if all_associations:
                self.stdout.write(f"Processing {len(all_associations)} total associations...")
                created_count = await self._process_associations_async(all_associations)
                self.stdout.write(self.style.SUCCESS(f"Created {created_count} associations"))

            # Update last sync time
            await self._update_last_sync_async(endpoint)
            
            self.stdout.write(self.style.SUCCESS(f"HubSpot contact-division associations sync complete. Processed {len(all_associations)} associations."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in sync process: {str(e)}"))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))

    async def _fetch_associations_adaptive(self, client, from_object, to_object, division_ids, start_date, end_date, limit=None, max_results_per_chunk=5000):
        """
        Adaptively fetch associations by breaking down division ID ranges when errors occur or too many results are returned.
        
        Args:
            client: HubspotClient instance
            from_object: Source object type
            to_object: Target object type
            division_ids: List of division IDs to process
            start_date: Start datetime for the range (None for full sync)
            end_date: End datetime for the range
            limit: Maximum number of associations to process (for testing)
            max_results_per_chunk: Maximum number of results per chunk before subdividing
        
        Returns:
            List of all associations fetched
        """
        all_associations = []
        
        # If no start_date, do a full fetch without date filtering
        if start_date is None:
            self.stdout.write("Performing full association fetch without date filtering...")
            return await self._fetch_all_associations_paginated(client, from_object, to_object, division_ids, limit)
        
        # Create initial ID ranges to process
        batch_size = 100  # Start with reasonable batch size
        pending_ranges = []
        
        for i in range(0, len(division_ids), batch_size):
            batch_division_ids = division_ids[i:i + batch_size]
            pending_ranges.append(batch_division_ids)
        
        while pending_ranges:
            current_batch = pending_ranges.pop(0)
            batch_size = len(current_batch)
            
            self.stdout.write(f"Processing batch of {batch_size} divisions...")
            
            try:
                # Try to fetch this chunk
                chunk_associations = await self._fetch_single_chunk(client, from_object, to_object, current_batch)
                
                if len(chunk_associations) > max_results_per_chunk and batch_size > 1:
                    # Too many results, subdivide the batch
                    self.stdout.write(f"⚠️ Chunk too large ({len(chunk_associations)} associations), subdividing...")
                    subdivisions = self._subdivide_id_range(current_batch, 4)
                    pending_ranges.extend(subdivisions)
                else:
                    # Acceptable chunk size
                    all_associations.extend(chunk_associations)
                    self.stdout.write(f"✅ Processed batch: {len(chunk_associations)} associations")
                    
                    # Apply limit if specified for testing
                    if limit and len(all_associations) >= limit:
                        self.stdout.write(f"Reached limit of {limit} associations for testing")
                        all_associations = all_associations[:limit]
                        break
            
            except Exception as e:
                error_msg = str(e)
                self.stdout.write(f"❌ Error fetching batch of {batch_size} divisions: {error_msg}")
                
                # If it's a large batch, try subdividing
                if batch_size > 1:
                    self.stdout.write("Subdividing batch due to error...")
                    subdivisions = self._subdivide_id_range(current_batch, 4)
                    pending_ranges.extend(subdivisions)
                else:
                    # Single division still failing, skip it but log the error
                    self.stdout.write(f"⚠️ Skipping problematic division: {current_batch[0]}")
                    logger.error(f"Failed to fetch associations for division {current_batch[0]}: {error_msg}")
        
        self.stdout.write(f"✅ Adaptive fetch complete: {len(all_associations)} total associations")
        return all_associations

    async def _fetch_all_associations_paginated(self, client, from_object, to_object, division_ids, limit=None):
        """Fetch all associations using standard pagination for full sync."""
        all_associations = []
        batch_size = 100  # Process divisions in batches
        
        for i in range(0, len(division_ids), batch_size):
            batch_division_ids = division_ids[i:i + batch_size]
            
            self.stdout.write(f"Processing batch {i//batch_size + 1}/{(len(division_ids) + batch_size - 1)//batch_size} ({len(batch_division_ids)} divisions)")
            
            try:
                batch_associations = await self._fetch_single_chunk(client, from_object, to_object, batch_division_ids)
                all_associations.extend(batch_associations)
                
                # Apply limit if specified for testing
                if limit and len(all_associations) >= limit:
                    self.stdout.write(f"Reached limit of {limit} associations for testing")
                    all_associations = all_associations[:limit]
                    break
                    
            except Exception as e:
                self.stdout.write(f"Error fetching batch {i//batch_size + 1}: {str(e)}")
                continue
        
        return all_associations

    async def _fetch_single_chunk(self, client, from_object, to_object, division_ids):
        """
        Fetch a single chunk of associations for the given division IDs.
        
        Args:
            client: HubspotClient instance
            from_object: Source object type
            to_object: Target object type
            division_ids: List of division IDs to process
            
        Returns:
            List of associations for this chunk
        """
        associations = []
        
        # Get associations for this batch of divisions
        data = await client.get_associations_page(
            from_object_type=from_object,
            to_object_type=to_object,
            inputs=division_ids,
            batch_size=len(division_ids),
            association_type_id=91  # Use the specific association type ID
        )
        
        results = data.get("results", [])
        
        if results:
            self.stdout.write(f"Found {len(results)} divisions with contact associations in this chunk")
            
            # Process results and create association objects
            for result in results:
                division_id = result.get('from', {}).get('id')
                associated_contacts = result.get('to', [])
                
                if associated_contacts:
                    for contact_assoc in associated_contacts:
                        contact_id = contact_assoc.get('toObjectId')
                        if contact_id and division_id:
                            associations.append({
                                'contact_id': contact_id,
                                'division_id': division_id
                            })
        
        return associations

    def _subdivide_id_range(self, id_list, num_subdivisions=4):
        """
        Subdivide a list of IDs into smaller equal chunks.
        
        Args:
            id_list: List of IDs to subdivide
            num_subdivisions: Number of equal subdivisions to create
            
        Returns:
            List of ID sublists for each subdivision
        """
        if len(id_list) <= num_subdivisions:
            # If we have few items, create individual sublists
            return [[id_item] for id_item in id_list]
        
        chunk_size = len(id_list) // num_subdivisions
        subdivisions = []
        
        for i in range(num_subdivisions):
            if i == num_subdivisions - 1:
                # Last chunk gets remaining items
                subdivisions.append(id_list[i * chunk_size:])
            else:
                subdivisions.append(id_list[i * chunk_size:(i + 1) * chunk_size])
        
        self.stdout.write(f"📋 Created {len(subdivisions)} subdivisions with ~{chunk_size} IDs each")
        return subdivisions

    @sync_to_async
    def _get_division_ids_async(self):
        """Get division IDs from database asynchronously"""
        return list(Hubspot_Division.objects.values_list('id', flat=True))

    @sync_to_async
    def _get_last_sync_async(self, endpoint):
        """Get the last sync time asynchronously"""
        try:
            history = Hubspot_SyncHistory.objects.get(endpoint=endpoint)
            return history.last_synced_at
        except Hubspot_SyncHistory.DoesNotExist:
            return None

    @sync_to_async
    def _process_associations_async(self, associations):
        """Process associations asynchronously"""
        return self._create_associations_batch(associations)

    @sync_to_async
    def _update_last_sync_async(self, endpoint):
        """Update the last sync time asynchronously"""
        Hubspot_SyncHistory.objects.update_or_create(
            endpoint=endpoint,
            defaults={'last_synced_at': timezone.now()}
        )

    def _create_associations_batch(self, associations_data):
        """Create a batch of associations from the fetched data."""
        if not associations_data:
            return 0
            
        # Convert association data to model instances
        associations_to_create = []
        for assoc_data in associations_data:
            associations_to_create.append(Hubspot_ContactDivisionAssociation(
                contact_id=assoc_data['contact_id'],
                division_id=assoc_data['division_id']
            ))
        
        try:
            Hubspot_ContactDivisionAssociation.objects.bulk_create(
                associations_to_create, 
                ignore_conflicts=True
            )
            created_count = len(associations_to_create)
            self.stdout.write(f"Successfully created {created_count} associations")
            return created_count
        except Exception as e:
            logger.error(f'Error creating associations batch: {str(e)}')
            self.stdout.write(self.style.ERROR(f'Error creating associations batch: {str(e)}'))
            return 0

    # Legacy method for backward compatibility
    def handle_legacy(self, *args, **options):
        """Original implementation kept for reference - not used"""
        pass
