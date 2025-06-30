import asyncio
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.hubspot.hubspot_client import HubspotClient
from ingestion.models.hubspot import (
    Hubspot_AppointmentContactAssociation,
    Hubspot_Appointment,
    Hubspot_Contact,
    Hubspot_SyncHistory
)

logger = logging.getLogger(__name__)

# Mapping association types to HubSpot object types
ASSOCATION_MAPPING = {
    'appointment_to_contact': {
        'from_object': '0-421',  # custom appointment object type
        'to_object': 'contacts'
    }
}

class Command(BaseCommand):
    help = 'Sync HubSpot appointment to contact associations'

    def handle(self, *args, **options):
        # Temporarily suppress hubspot_client error logs that are actually successful responses
        hubspot_logger = logging.getLogger('ingestion.hubspot.hubspot_client')
        original_level = hubspot_logger.level
        hubspot_logger.setLevel(logging.CRITICAL)
        
        try:
            from_object = ASSOCATION_MAPPING['appointment_to_contact']['from_object']
            to_object = ASSOCATION_MAPPING['appointment_to_contact']['to_object']

            self.stdout.write(f"Starting HubSpot associations sync")
            client = HubspotClient()
            created_count = 0
            batch = []  # Initialize batch for collecting associations
            
            # Sync associations per appointment
            appointment_ids = Hubspot_Appointment.objects.values_list('id', flat=True)
            appointment_ids = list(appointment_ids)  # Ensure it's a list
            total_batches = (len(appointment_ids) + 999) // 1000  # Calculate total batches

            # Fetch associations in bulk
            batch_size = 1000  # Adjust batch size for bulk fetching
            for i in range(0, len(appointment_ids), batch_size):
                batch_ids = appointment_ids[i:i + batch_size]
                batch_num = i//batch_size + 1
                
                self.stdout.write(f"Processing batch {batch_num}/{total_batches} ({len(batch_ids)} appointments)")
                
                try:
                    results = asyncio.run(
                        client.get_bulk_associations(
                            from_object_type=from_object,
                            to_object_type=to_object,
                            inputs=batch_ids
                        )
                    )
                    
                    # Process successful results
                    if isinstance(results, dict) and 'results' in results:
                        associations_data = results['results']
                        errors = results.get('errors', [])
                        
                        # Log only actual errors (not NO_ASSOCIATIONS_FOUND which is expected)
                        actual_errors = [err for err in errors if 'NO_ASSOCIATIONS_FOUND' not in err.get('subCategory', '')]
                        if actual_errors:
                            logger.warning(f"Found {len(actual_errors)} unexpected errors in batch {batch_num}")
                        
                        # Calculate counts outside f-string to avoid bracket issues
                        no_assoc_count = len([e for e in errors if 'NO_ASSOCIATIONS_FOUND' in e.get('subCategory', '')])
                        self.stdout.write(f"  Found {len(associations_data)} appointments with associations, {no_assoc_count} without associations")
                    else:
                        associations_data = results
                        self.stdout.write(f"  Processing {len(associations_data)} association results")
                        
                except Exception as e:
                    logger.exception(f"Error fetching bulk associations for appointments batch {batch_num}")
                    raise CommandError(f"Bulk sync failed on batch {batch_num}: {e}")

                for assoc in associations_data:
                    # Parse the HubSpot API response structure
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

                        batch.append(Hubspot_AppointmentContactAssociation(
                            appointment_id=appointment_id,
                            contact_id=contact_id
                        ))

                # Save batch periodically to avoid memory issues
                if len(batch) >= 500:  # Reduced batch size for more frequent saves
                    Hubspot_AppointmentContactAssociation.objects.bulk_create(batch, ignore_conflicts=True)
                    created_count += len(batch)
                    self.stdout.write(f"  Saved {len(batch)} associations (total: {created_count})")
                    batch = []  # Reset batch

            # Process any remaining associations in the batch
            if batch:
                Hubspot_AppointmentContactAssociation.objects.bulk_create(batch, ignore_conflicts=True)
                created_count += len(batch)
                self.stdout.write(f"  Saved final {len(batch)} associations")

            # Update sync history
            Hubspot_SyncHistory.objects.update_or_create(
                endpoint='associations_appointment_to_contact',
                defaults={'last_synced_at': timezone.now()}
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"HubSpot associations sync complete. Created {created_count} new associations."
                )
            )
        
        finally:
            # Restore original logging level
            hubspot_logger.setLevel(original_level)
