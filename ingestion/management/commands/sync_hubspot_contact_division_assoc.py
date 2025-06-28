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

    def handle(self, *args, **options):
        from_object = ASSOCATION_MAPPING['division_to_contact']['from_object']
        to_object = ASSOCATION_MAPPING['division_to_contact']['to_object']

        self.stdout.write(f"Starting HubSpot division_to_contact associations sync")
        client = HubspotClient()
        created_count = 0
        batch = []  # Initialize batch for collecting associations
        
        # Apply limit if specified for testing
        limit = options.get('limit')
        if limit:
            self.stdout.write(f"Limited mode: will process up to {limit} associations for testing")
        else:
            self.stdout.write(f"Full sync mode: downloading all division_to_contact associations from HubSpot")

        try:
            # First, get all available association labels
            self.stdout.write(f"Fetching association labels between {from_object} and {to_object}...")
            labels = asyncio.run(
                client.get_association_labels(
                    from_object_type=from_object,
                    to_object_type=to_object
                )
            )
            
            if not labels:
                self.stdout.write(self.style.WARNING("No association labels found between these object types"))
                return
            
            self.stdout.write(f"Found {len(labels)} association labels:")
            for label in labels:
                label_name = label.get('label', 'Unknown')
                label_type = label.get('typeId', 'Unknown')
                self.stdout.write(f"  - {label_name} (Type ID: {label_type})")
            
            # Get all division IDs from our local database to query for their associations
            self.stdout.write(f"Getting division IDs from local database...")
            division_ids = list(Hubspot_Division.objects.values_list('id', flat=True))
            
            if not division_ids:
                self.stdout.write(self.style.WARNING("No divisions found in local database. Please sync divisions first."))
                return
            
            self.stdout.write(f"Found {len(division_ids)} divisions to check for contact associations")
            
            # Fetch associations in batches using the v4 batch read endpoint
            processed_associations = 0
            batch_size = 100  # HubSpot allows up to 1000, but let's be conservative
            
            for i in range(0, len(division_ids), batch_size):
                batch_division_ids = division_ids[i:i + batch_size]
                
                self.stdout.write(f"Processing batch {i//batch_size + 1}/{(len(division_ids) + batch_size - 1)//batch_size} ({len(batch_division_ids)} divisions)")
                
                # Get associations for this batch of divisions
                data = asyncio.run(
                    client.get_associations_page(
                        from_object_type=from_object,
                        to_object_type=to_object,
                        inputs=batch_division_ids,
                        batch_size=len(batch_division_ids),
                        association_type_id=91  # Use the specific association type ID we found
                    )
                )
                
                results = data.get("results", [])
                
                if results:
                    self.stdout.write(f"Found {len(results)} divisions with contact associations in this batch")
                    
                    # Process results and create associations
                    for result in results:
                        division_id = result.get('from', {}).get('id')
                        associated_contacts = result.get('to', [])
                        
                        if associated_contacts:
                            self.stdout.write(f"Division {division_id} has {len(associated_contacts)} contact associations")
                            
                            for contact_assoc in associated_contacts:
                                contact_id = contact_assoc.get('toObjectId')
                                if contact_id and division_id:
                                    batch.append(Hubspot_ContactDivisionAssociation(
                                        contact_id=contact_id,
                                        division_id=division_id
                                    ))
                                    processed_associations += 1

                                    # Batch create to avoid memory issues
                                    if len(batch) >= 1000:
                                        self._create_associations_batch(batch)
                                        created_count += len(batch)
                                        batch = []
                                        
                                    # Apply limit if specified for testing
                                    if limit and processed_associations >= limit:
                                        self.stdout.write(f"Reached limit of {limit} associations for testing")
                                        break
                            
                            # Apply limit if specified for testing
                            if limit and processed_associations >= limit:
                                break
                else:
                    self.stdout.write(f"No associations found for this batch of divisions")
                
                # Apply limit if specified for testing
                if limit and processed_associations >= limit:
                    break

            self.stdout.write(f"Processed {processed_associations} total associations")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error fetching associations from HubSpot: {str(e)}')
            )
            logger.error(f'Error fetching associations: {str(e)}')

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
