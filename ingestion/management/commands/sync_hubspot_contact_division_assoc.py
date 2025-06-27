import asyncio
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

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
    'contact_to_division': {
        'from_object': 'contacts',  # contact object type
        'to_object': '2-37778609'   # custom division object type
    }
}

class Command(BaseCommand):
    help = 'Sync HubSpot contact to division associations'

    def handle(self, *args, **options):
        from_object = ASSOCATION_MAPPING['contact_to_division']['from_object']
        to_object = ASSOCATION_MAPPING['contact_to_division']['to_object']

        self.stdout.write(f"Starting HubSpot contact-to-division associations sync")
        client = HubspotClient()
        created_count = 0
        batch = []  # Initialize batch for collecting associations
        
        # Sync associations per contact
        contact_ids = Hubspot_Contact.objects.values_list('id', flat=True)
        contact_ids = list(contact_ids)  # Ensure it's a list

        # Fetch associations in bulk
        batch_size = 1000  # Adjust batch size for bulk fetching
        for i in range(0, len(contact_ids), batch_size):
            batch_ids = contact_ids[i:i + batch_size]
            try:
                results = asyncio.run(
                    client.get_bulk_associations(
                        from_object_type=from_object,
                        to_object_type=to_object,
                        inputs=batch_ids
                    )
                )

                # Process results and create associations
                for result in results:
                    contact_id = result.get('from', {}).get('id')
                    associations = result.get('to', [])

                    for association in associations:
                        division_id = association.get('id')
                        if division_id:
                            batch.append(Hubspot_ContactDivisionAssociation(
                                contact_id=contact_id,
                                division_id=division_id
                            ))

                            # Batch create to avoid memory issues
                            if len(batch) >= 1000:
                                self._create_associations_batch(batch)
                                created_count += len(batch)
                                batch = []

                self.stdout.write(f"Processed batch {i//batch_size + 1}/{(len(contact_ids) + batch_size - 1)//batch_size}")

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing batch {i//batch_size + 1}: {str(e)}')
                )
                logger.error(f'Error processing batch: {str(e)}')

        # Create remaining associations
        if batch:
            self._create_associations_batch(batch)
            created_count += len(batch)

        self.stdout.write(
            self.style.SUCCESS(f'Contact-to-division association sync completed! Created {created_count} associations.')
        )

        # Update sync history
        Hubspot_SyncHistory.objects.update_or_create(
            endpoint='associations_contact_to_division',
            defaults={'last_synced_at': timezone.now()}
        )

    def _create_associations_batch(self, batch):
        """Create a batch of associations, handling duplicates gracefully."""
        try:
            Hubspot_ContactDivisionAssociation.objects.bulk_create(batch, ignore_conflicts=True)
        except Exception as e:
            logger.error(f'Error creating associations batch: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Error creating associations batch: {str(e)}')
            )
