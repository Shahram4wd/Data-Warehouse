import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Tuple
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from asgiref.sync import sync_to_async

from ingestion.hubspot.hubspot_client import HubspotClient
from ingestion.models.hubspot import (
    Hubspot_AppointmentContactAssociation,
    Hubspot_Appointment,
    Hubspot_Contact,
    Hubspot_SyncHistory
)

logger = logging.getLogger(__name__)

# Mapping association types to HubSpot object types and association type IDs
ASSOCATION_MAPPING = {
    'appointment_to_contact': {
        'from_object': '0-421',  # custom appointment object type
        'to_object': 'contacts',
        'association_types': [906]  # Appointment to contact
    },
    'contact_to_appointment': {
        'from_object': 'contacts',
        'to_object': '0-421',  # custom appointment object type  
        'association_types': [907]  # Contact to appointment
    }
}

class Command(BaseCommand):
    help = 'Sync HubSpot appointment to contact associations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform a full sync (clear existing data and re-sync all)',
        )
        parser.add_argument(
            '--contact-id',
            type=str,
            help='Sync associations for a specific contact ID only',
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
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of associations to process for testing (default: process all)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting HubSpot appointment-contact associations sync..."))
        
        # Run the async sync
        try:
            asyncio.run(self.sync_associations(options))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Sync failed: {str(e)}'))
            logger.error(f"HubSpot appointment-contact associations sync failed: {str(e)}")

    async def sync_associations(self, options):
        """Main sync logic with adaptive chunking"""
        # Temporarily suppress hubspot_client error logs that are actually successful responses
        hubspot_logger = logging.getLogger('ingestion.hubspot.hubspot_client')
        original_level = hubspot_logger.level
        hubspot_logger.setLevel(logging.CRITICAL)
        
        try:
            start_time = timezone.now()
            
            # Get options
            full_sync = options.get("full")
            contact_id = options.get("contact_id")
            lastmodifieddate = options.get("lastmodifieddate")
            limit = options.get('limit')
            
            # Get the last sync time
            endpoint = "appointment_contact_associations"
            
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
            
            # Clear existing associations if full sync
            if full_sync:
                self.stdout.write("Clearing existing associations...")
                deleted_count = await self._clear_existing_associations_async()
                self.stdout.write(f"Deleted {deleted_count} existing associations")
            
            # Track processed associations to avoid duplicates
            seen_associations = set()
            all_associations = []
            
            # Handle specific contact ID sync
            if contact_id:
                self.stdout.write(f"Syncing associations for contact {contact_id}")
                contact_associations = await self._fetch_contact_associations_adaptive(client, [contact_id], limit)
                all_associations.extend(contact_associations)
            else:
                # Bulk sync logic for all appointments with adaptive chunking
                self.stdout.write("Starting bulk appointment-contact associations sync with adaptive chunking...")
                
                # Get all appointment IDs from database
                appointment_ids = await self._get_appointment_ids_async()
                self.stdout.write(f"Found {len(appointment_ids)} appointments to check for contact associations")
                
                # Use adaptive chunking to fetch appointment associations
                appointment_associations = await self._fetch_appointment_associations_adaptive(
                    client, appointment_ids, last_sync, timezone.now(), limit
                )
                all_associations.extend(appointment_associations)
                
                # REVERSE DIRECTION SYNC with adaptive chunking
                self.stdout.write("Starting comprehensive reverse direction sync (contact->appointment) with adaptive chunking...")
                
                # Get ALL contact IDs from database
                contact_ids = await self._get_contact_ids_async()
                self.stdout.write(f"Found {len(contact_ids)} contacts to check for appointment associations")
                
                # Use adaptive chunking to fetch contact associations
                contact_associations = await self._fetch_contact_associations_adaptive(
                    client, contact_ids, limit
                )
                all_associations.extend(contact_associations)
            
            # Process all fetched associations
            if all_associations:
                self.stdout.write(f"Processing {len(all_associations)} total associations...")
                created_count = await self._process_associations_async(all_associations)
                self.stdout.write(self.style.SUCCESS(f"Created {created_count} associations"))
            
            # Update last sync time
            await self._update_last_sync_async(endpoint)
            
            self.stdout.write(self.style.SUCCESS(f"HubSpot appointment-contact associations sync complete. Processed {len(all_associations)} associations."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in sync process: {str(e)}"))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            
            # Record failed sync
            await self._update_last_sync_async('appointment_contact_associations_failed')
            raise CommandError(f"Sync failed: {e}")
        
        finally:
            # Restore original logging level
            hubspot_logger.setLevel(original_level)

    async def _fetch_appointment_associations_adaptive(self, client, appointment_ids, start_date, end_date, limit=None, max_results_per_chunk=3000):
        """
        Adaptively fetch appointment associations by breaking down ID ranges when errors occur or too many results are returned.
        
        Args:
            client: HubspotClient instance
            appointment_ids: List of appointment IDs to process
            start_date: Start datetime for the range (None for full sync)
            end_date: End datetime for the range
            limit: Maximum number of associations to process (for testing)
            max_results_per_chunk: Maximum number of results per chunk before subdividing
        
        Returns:
            List of all associations fetched
        """
        all_associations = []
        
        # Get association types
        try:
            association_types = await client.get_association_labels(
                from_object_type="0-421",  # custom appointment object type
                to_object_type="contacts"
            )
            type_ids = [assoc_type['typeId'] for assoc_type in association_types]
            self.stdout.write(f"Found appointment->contact types: {type_ids}")
        except Exception as e:
            logger.warning(f"Could not fetch association types, using defaults: {e}")
            type_ids = [906, 907]  # Include both default types
        
        # Create initial ID ranges to process
        batch_size = 1000  # Start with reasonable batch size
        pending_ranges = []
        
        for i in range(0, len(appointment_ids), batch_size):
            batch_appointment_ids = appointment_ids[i:i + batch_size]
            pending_ranges.append(batch_appointment_ids)
        
        while pending_ranges:
            current_batch = pending_ranges.pop(0)
            batch_size = len(current_batch)
            
            self.stdout.write(f"Processing appointment batch of {batch_size} IDs...")
            
            try:
                # Try to fetch this chunk
                chunk_associations = await self._fetch_single_appointment_chunk(client, current_batch, type_ids)
                
                if len(chunk_associations) > max_results_per_chunk and batch_size > 1:
                    # Too many results, subdivide the batch
                    self.stdout.write(f"⚠️ Chunk too large ({len(chunk_associations)} associations), subdividing...")
                    subdivisions = self._subdivide_id_range(current_batch, 4)
                    pending_ranges.extend(subdivisions)
                else:
                    # Acceptable chunk size
                    all_associations.extend(chunk_associations)
                    self.stdout.write(f"✅ Processed appointment batch: {len(chunk_associations)} associations")
                    
                    # Apply limit if specified for testing
                    if limit and len(all_associations) >= limit:
                        self.stdout.write(f"Reached limit of {limit} associations for testing")
                        all_associations = all_associations[:limit]
                        break
            
            except Exception as e:
                error_msg = str(e)
                self.stdout.write(f"❌ Error fetching appointment batch of {batch_size} IDs: {error_msg}")
                
                # If it's a large batch, try subdividing
                if batch_size > 1:
                    self.stdout.write("Subdividing appointment batch due to error...")
                    subdivisions = self._subdivide_id_range(current_batch, 4)
                    pending_ranges.extend(subdivisions)
                else:
                    # Single appointment still failing, skip it but log the error
                    self.stdout.write(f"⚠️ Skipping problematic appointment: {current_batch[0]}")
                    logger.error(f"Failed to fetch associations for appointment {current_batch[0]}: {error_msg}")
        
        self.stdout.write(f"✅ Adaptive appointment fetch complete: {len(all_associations)} total associations")
        return all_associations

    async def _fetch_contact_associations_adaptive(self, client, contact_ids, limit=None, max_results_per_chunk=3000):
        """
        Adaptively fetch contact associations by breaking down ID ranges when errors occur or too many results are returned.
        
        Args:
            client: HubspotClient instance
            contact_ids: List of contact IDs to process
            limit: Maximum number of associations to process (for testing)
            max_results_per_chunk: Maximum number of results per chunk before subdividing
        
        Returns:
            List of all associations fetched
        """
        all_associations = []
        
        # Get reverse association types
        try:
            reverse_association_types = await client.get_association_labels(
                from_object_type="contacts",
                to_object_type="0-421"
            )
            reverse_type_ids = [assoc_type['typeId'] for assoc_type in reverse_association_types]
            self.stdout.write(f"Found contact->appointment types: {reverse_type_ids}")
        except Exception as e:
            logger.warning(f"Could not fetch reverse association types, using default: {e}")
            reverse_type_ids = [907]  # Default contact->appointment type
        
        # Create initial ID ranges to process
        batch_size = 100  # Smaller batch for contacts as they tend to have more associations
        pending_ranges = []
        
        for i in range(0, len(contact_ids), batch_size):
            batch_contact_ids = contact_ids[i:i + batch_size]
            pending_ranges.append(batch_contact_ids)
        
        while pending_ranges:
            current_batch = pending_ranges.pop(0)
            batch_size = len(current_batch)
            
            self.stdout.write(f"Processing contact batch of {batch_size} IDs...")
            
            try:
                # Try to fetch this chunk
                chunk_associations = await self._fetch_single_contact_chunk(client, current_batch, reverse_type_ids)
                
                if len(chunk_associations) > max_results_per_chunk and batch_size > 1:
                    # Too many results, subdivide the batch
                    self.stdout.write(f"⚠️ Chunk too large ({len(chunk_associations)} associations), subdividing...")
                    subdivisions = self._subdivide_id_range(current_batch, 4)
                    pending_ranges.extend(subdivisions)
                else:
                    # Acceptable chunk size
                    all_associations.extend(chunk_associations)
                    self.stdout.write(f"✅ Processed contact batch: {len(chunk_associations)} associations")
                    
                    # Apply limit if specified for testing
                    if limit and len(all_associations) >= limit:
                        self.stdout.write(f"Reached limit of {limit} associations for testing")
                        all_associations = all_associations[:limit]
                        break
            
            except Exception as e:
                error_msg = str(e)
                self.stdout.write(f"❌ Error fetching contact batch of {batch_size} IDs: {error_msg}")
                
                # If it's a large batch, try subdividing
                if batch_size > 1:
                    self.stdout.write("Subdividing contact batch due to error...")
                    subdivisions = self._subdivide_id_range(current_batch, 4)
                    pending_ranges.extend(subdivisions)
                else:
                    # Single contact still failing, skip it but log the error
                    self.stdout.write(f"⚠️ Skipping problematic contact: {current_batch[0]}")
                    logger.error(f"Failed to fetch associations for contact {current_batch[0]}: {error_msg}")
        
        self.stdout.write(f"✅ Adaptive contact fetch complete: {len(all_associations)} total associations")
        return all_associations

    async def _fetch_single_appointment_chunk(self, client, appointment_ids, type_ids):
        """
        Fetch a single chunk of appointment associations for the given appointment IDs.
        
        Args:
            client: HubspotClient instance
            appointment_ids: List of appointment IDs to process
            type_ids: List of association type IDs
            
        Returns:
            List of associations for this chunk
        """
        associations = []
        
        try:
            results = await client.get_bulk_associations_with_types(
                from_object_type="0-421",  # custom appointment object type
                to_object_type="contacts",
                inputs=appointment_ids,
                association_types=type_ids
            )
            
            # Process successful results
            if isinstance(results, dict) and 'results' in results:
                associations_data = results['results']
                errors = results.get('errors', [])
                
                # Log only actual errors (not NO_ASSOCIATIONS_FOUND which is expected)
                actual_errors = [err for err in errors if 'NO_ASSOCIATIONS_FOUND' not in err.get('subCategory', '')]
                if actual_errors:
                    logger.warning(f"Found {len(actual_errors)} unexpected errors in appointment chunk")
                
                # Calculate counts
                no_assoc_count = len([e for e in errors if 'NO_ASSOCIATIONS_FOUND' in e.get('subCategory', '')])
                self.stdout.write(f"  Found {len(associations_data)} appointments with associations, {no_assoc_count} without associations")
            else:
                associations_data = results
                self.stdout.write(f"  Processing {len(associations_data)} association results")
            
            # Process the associations
            for assoc in associations_data:
                from_obj = assoc.get('from', {})
                to_objects = assoc.get('to', [])
                
                appointment_id = from_obj.get('id')
                if not appointment_id or not to_objects:
                    continue
                
                # Process each associated contact
                for to_obj in to_objects:
                    contact_id = str(to_obj.get('toObjectId'))
                    if not contact_id:
                        continue
                    
                    associations.append({
                        'appointment_id': appointment_id,
                        'contact_id': contact_id
                    })
            
        except Exception as e:
            raise e
        
        return associations

    async def _fetch_single_contact_chunk(self, client, contact_ids, reverse_type_ids):
        """
        Fetch a single chunk of contact associations for the given contact IDs.
        
        Args:
            client: HubspotClient instance
            contact_ids: List of contact IDs to process
            reverse_type_ids: List of association type IDs for reverse direction
            
        Returns:
            List of associations for this chunk
        """
        associations = []
        
        try:
            reverse_results = await client.get_bulk_associations_with_types(
                from_object_type="contacts",
                to_object_type="0-421",
                inputs=contact_ids,
                association_types=reverse_type_ids
            )
            
            # Process reverse results
            if isinstance(reverse_results, dict) and 'results' in reverse_results:
                reverse_associations_data = reverse_results['results']
                reverse_errors = reverse_results.get('errors', [])
                
                reverse_no_assoc_count = len([e for e in reverse_errors if 'NO_ASSOCIATIONS_FOUND' in e.get('subCategory', '')])
                self.stdout.write(f"  Found {len(reverse_associations_data)} contacts with appointment associations, {reverse_no_assoc_count} without")
            else:
                reverse_associations_data = reverse_results
            
            # Process the reverse associations
            for assoc in reverse_associations_data:
                from_obj = assoc.get('from', {})
                to_objects = assoc.get('to', [])
                
                contact_id = from_obj.get('id')
                if not contact_id or not to_objects:
                    continue
                
                # Process each associated appointment
                for to_obj in to_objects:
                    appointment_id = str(to_obj.get('toObjectId'))
                    if not appointment_id:
                        continue
                    
                    associations.append({
                        'appointment_id': appointment_id,
                        'contact_id': contact_id
                    })
            
        except Exception as e:
            raise e
        
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
    def _get_appointment_ids_async(self):
        """Get appointment IDs from database asynchronously"""
        return list(Hubspot_Appointment.objects.values_list('id', flat=True))

    @sync_to_async
    def _get_contact_ids_async(self):
        """Get contact IDs from database asynchronously"""
        return list(Hubspot_Contact.objects.values_list('id', flat=True))

    @sync_to_async
    def _get_last_sync_async(self, endpoint):
        """Get the last sync time asynchronously"""
        try:
            history = Hubspot_SyncHistory.objects.get(endpoint=endpoint)
            return history.last_synced_at
        except Hubspot_SyncHistory.DoesNotExist:
            return None

    @sync_to_async
    def _clear_existing_associations_async(self):
        """Clear existing associations asynchronously"""
        return Hubspot_AppointmentContactAssociation.objects.all().delete()[0]

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
        
        # Track processed associations to avoid duplicates
        seen_associations = set()
        associations_to_create = []
        
        for assoc_data in associations_data:
            association_key = (str(assoc_data['appointment_id']), str(assoc_data['contact_id']))
            if association_key not in seen_associations:
                seen_associations.add(association_key)
                associations_to_create.append(Hubspot_AppointmentContactAssociation(
                    appointment_id=assoc_data['appointment_id'],
                    contact_id=assoc_data['contact_id']
                ))
        
        try:
            Hubspot_AppointmentContactAssociation.objects.bulk_create(
                associations_to_create, 
                ignore_conflicts=True
            )
            created_count = len(associations_to_create)
            self.stdout.write(f"Successfully created {created_count} unique associations")
            return created_count
        except Exception as e:
            logger.error(f'Error creating associations batch: {str(e)}')
            self.stdout.write(self.style.ERROR(f'Error creating associations batch: {str(e)}'))
            return 0

    # Legacy method for backward compatibility
    def handle_legacy(self, *args, **options):
        """Original implementation kept for reference - not used"""
        pass
