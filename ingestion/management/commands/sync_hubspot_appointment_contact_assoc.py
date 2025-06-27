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
        from_object = ASSOCATION_MAPPING['appointment_to_contact']['from_object']
        to_object = ASSOCATION_MAPPING['appointment_to_contact']['to_object']

        self.stdout.write(f"Starting HubSpot associations sync")
        client = HubspotClient()
        created_count = 0
        batch = []  # Initialize batch for collecting associations
        
        # Sync associations per appointment
        appointment_ids = Hubspot_Appointment.objects.values_list('id', flat=True)
        appointment_ids = list(appointment_ids)  # Ensure it's a list

        # Fetch associations in bulk
        batch_size = 1000  # Adjust batch size for bulk fetching
        for i in range(0, len(appointment_ids), batch_size):
            batch_ids = appointment_ids[i:i + batch_size]
            try:
                results = asyncio.run(
                    client.get_bulk_associations(
                        from_object_type=from_object,
                        to_object_type=to_object,
                        inputs=batch_ids
                    )
                )
            except Exception as e:
                logger.exception(f"Error fetching bulk associations for appointments {batch_ids}")
                raise CommandError(f"Bulk sync failed on batch {batch_ids}: {e}")

            for assoc in results:
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

                if len(batch) >= batch_size:
                    Hubspot_AppointmentContactAssociation.objects.bulk_create(batch, ignore_conflicts=True)
                    created_count += len(batch)
                    batch = []  # Reset batch

        # Process any remaining associations in the batch
        if batch:
            Hubspot_AppointmentContactAssociation.objects.bulk_create(batch, ignore_conflicts=True)
            created_count += len(batch)

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
