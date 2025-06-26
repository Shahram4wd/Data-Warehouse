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
    help = 'Sync HubSpot associations between appointments and contacts'

    def handle(self, *args, **options):
        from_object = ASSOCATION_MAPPING['appointment_to_contact']['from_object']
        to_object = ASSOCATION_MAPPING['appointment_to_contact']['to_object']

        self.stdout.write(f"Starting HubSpot associations sync")
        client = HubspotClient()
        created_count = 0
        # Sync associations per appointment
        appointment_ids = Hubspot_Appointment.objects.values_list('id', flat=True)
        appointment_ids = list(appointment_ids)  # Ensure it's a list

        # Initialize batch
        batch_size = 100
        batch = []

        for appt_id in appointment_ids:
            page_token = None
            while True:
                try:
                    results, page_token = asyncio.run(
                        client.get_object_associations(
                            from_object=from_object,
                            object_id=appt_id,
                            to_object=to_object,
                            page_token=page_token,
                            limit=100
                        )
                    )
                except Exception as e:
                    logger.exception(f"Error fetching associations for appointment {appt_id}")
                    raise CommandError(f"Sync failed on {appt_id}: {e}")

                if not results:
                    break

                for assoc in results:
                    contact_id = assoc.get('id') or assoc.get('toObjectId')
                    if not contact_id:
                        continue

                    batch.append(Hubspot_AppointmentContactAssociation(
                        appointment_id=appt_id,
                        contact_id=contact_id
                    ))

                    if len(batch) >= batch_size:
                        Hubspot_AppointmentContactAssociation.objects.bulk_create(batch, ignore_conflicts=True)
                        created_count += len(batch)
                        batch = []  # Reset batch

                if not page_token:
                    break

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
