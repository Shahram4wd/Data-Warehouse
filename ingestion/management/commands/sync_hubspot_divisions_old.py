import asyncio
import logging
from datetime import datetime
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from tqdm import tqdm

from ingestion.hubspot.hubspot_client import HubspotClient
from ingestion.models.hubspot import Hubspot_Division, Hubspot_SyncHistory

logger = logging.getLogger(__name__)

BATCH_SIZE = 100  # Adjust batch size to process more divisions per checkpoint

class Command(BaseCommand):
    help = "Sync divisions from HubSpot custom object 2-37778609"

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform a full sync instead of incremental."
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Show debug output"
        )
        parser.add_argument(
            "--pages",
            type=int,
            default=0,
            help="Maximum number of pages to process (0 for unlimited)"
        )
        parser.add_argument(
            "--checkpoint",
            type=int,
            default=5,
            help="Save progress to database after every N pages (default 5)"
        )
        parser.add_argument(
            "--lastmodifieddate",
            type=str,
            help="Filter divisions modified after this date (YYYY-MM-DD format)"
        )

    def handle(self, *args, **options):
        full_sync = options.get("full")
        max_pages = options.get("pages", 0)
        checkpoint_interval = options.get("checkpoint", 5)
        lastmodifieddate = options.get("lastmodifieddate")
        token = settings.HUBSPOT_API_TOKEN

        if not token:
            raise CommandError("HUBSPOT_API_TOKEN is not set in settings or environment variables.")

        self.stdout.write(self.style.SUCCESS("Starting HubSpot divisions sync..."))
        
        # Get the last sync time
        endpoint = "divisions"  # Custom object endpoint
        
        # Priority: 1) --lastmodifieddate parameter, 2) database last sync, 3) full sync
        if lastmodifieddate:
            # Parse the provided date
            try:
                last_sync = datetime.strptime(lastmodifieddate, "%Y-%m-%d")
                # Make it timezone aware
                last_sync = timezone.make_aware(last_sync)
                self.stdout.write(f"Using provided lastmodifieddate filter: {lastmodifieddate}")
            except ValueError:
                raise CommandError(f"Invalid date format for --lastmodifieddate. Use YYYY-MM-DD format.")
        elif full_sync:
            last_sync = None
        else:
            last_sync = self.get_last_sync(endpoint)
        
        if last_sync:
            self.stdout.write(f"Performing delta sync since {last_sync}")
        else:
            self.stdout.write("Performing full sync")
        
        # Process divisions synchronously
        try:
            # Fetch all pages of data
            all_divisions = []
            total_pages = 0
            
            # Start async event loop
            next_page_token = None
            client = HubspotClient(token)
            
            self.stdout.write("Starting to fetch divisions from HubSpot...")
            self.stdout.write(f"Using batch size: {BATCH_SIZE}")
            
            while True:
                # Check if we've reached the maximum number of pages
                if max_pages > 0 and total_pages >= max_pages:
                    self.stdout.write(f"Reached maximum page limit of {max_pages}")
                    break

                # Fetch a single page
                total_pages += 1
                self.stdout.write(f"Fetching page {total_pages}...")

                # Log the parameters being sent
                self.stdout.write(f"Fetching page from {client.BASE_URL} with endpoint: objects/2-37778609")

                page_result = asyncio.run(client.get_custom_object_page(
                    object_type="2-37778609",  # Division custom object type
                    last_sync=last_sync,
                    page_token=next_page_token
                ))

                if not page_result or not page_result[0]:
                    self.stdout.write("No more data to fetch")
                    break

                page_data, next_page_token = page_result
                self.stdout.write(f"Retrieved {len(page_data)} divisions")
                all_divisions.extend(page_data)

                # Debug: Log retrieved division IDs
                self.stdout.write(f"Retrieved division IDs: {[division.get('id') for division in page_data]}")

                # Save data if we've reached a checkpoint
                if len(all_divisions) >= BATCH_SIZE:
                    self.stdout.write(f"Processing checkpoint at page {total_pages}...")
                    self.process_divisions_batch(all_divisions[:BATCH_SIZE])
                    all_divisions = all_divisions[BATCH_SIZE:]  # Keep remaining divisions

                # If no next page token, we're done
                if not next_page_token:
                    self.stdout.write("No more pages available")
                    break

            # Process any remaining divisions
            if all_divisions:
                self.stdout.write(f"Processing final batch of {len(all_divisions)} divisions...")
                self.process_divisions_batch(all_divisions)

            # Update last sync time
            self.update_last_sync(endpoint)

            self.stdout.write(self.style.SUCCESS(f"HubSpot divisions sync complete. Processed {total_pages} pages."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in sync process: {str(e)}"))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))

    def process_divisions_batch(self, divisions):
        """Process a batch of divisions and save them to the database."""
        if not divisions:
            return 0, 0
            
        created = 0
        updated = 0
        
        self.stdout.write(f"Processing {len(divisions)} divisions...")
        
        # Collect existing division IDs
        division_ids = [division.get('id') for division in divisions if division.get('id')]
        existing_divisions = Hubspot_Division.objects.in_bulk(division_ids)
        
        to_create = []
        to_update = []
        
        # Process each division with progress bar
        for division in tqdm(divisions, desc="Processing divisions"):
            try:
                # Get basic info
                record_id = division.get('id')
                if not record_id:
                    self.stdout.write(f"Skipping division without ID: {division}")
                    continue

                # Extract properties from the division
                props = division.get('properties', {})
                
                # Map properties to model fields
                division_data = {
                    'hs_object_id': props.get('hs_object_id'),
                    'division_name': props.get('division_name'),
                    'division_label': props.get('division_label') or props.get('label'),
                    'division_code': props.get('division_code') or props.get('code'),
                    'status': props.get('status'),
                    'region': props.get('region'),
                    'manager_name': props.get('manager_name'),
                    'manager_email': props.get('manager_email'),
                    'phone': props.get('phone'),
                    'address1': props.get('address1'),
                    'address2': props.get('address2'),
                    'city': props.get('city'),
                    'state': props.get('state'),
                    'zip': props.get('zip'),
                    'hs_createdate': self._parse_datetime(props.get('hs_createdate')),
                    'hs_lastmodifieddate': self._parse_datetime(props.get('hs_lastmodifieddate')),
                    'hs_pipeline': props.get('hs_pipeline'),
                    'hs_pipeline_stage': props.get('hs_pipeline_stage'),
                    # HubSpot system fields
                    'hs_all_accessible_team_ids': props.get('hs_all_accessible_team_ids'),
                    'hs_all_assigned_business_unit_ids': props.get('hs_all_assigned_business_unit_ids'),
                    'hs_all_owner_ids': props.get('hs_all_owner_ids'),
                    'hs_all_team_ids': props.get('hs_all_team_ids'),
                    'hs_created_by_user_id': props.get('hs_created_by_user_id'),
                    'hs_merged_object_ids': props.get('hs_merged_object_ids'),
                    'hs_object_source': props.get('hs_object_source'),
                    'hs_object_source_detail_1': props.get('hs_object_source_detail_1'),
                    'hs_object_source_detail_2': props.get('hs_object_source_detail_2'),
                    'hs_object_source_detail_3': props.get('hs_object_source_detail_3'),
                    'hs_object_source_id': props.get('hs_object_source_id'),
                    'hs_object_source_label': props.get('hs_object_source_label'),
                    'hs_object_source_user_id': props.get('hs_object_source_user_id'),
                    'hs_owning_teams': props.get('hs_owning_teams'),
                    'hs_read_only': props.get('hs_read_only') == 'true' if props.get('hs_read_only') else None,
                    'hs_shared_team_ids': props.get('hs_shared_team_ids'),
                    'hs_shared_user_ids': props.get('hs_shared_user_ids'),
                    'hs_unique_creation_key': props.get('hs_unique_creation_key'),
                    'hs_updated_by_user_id': props.get('hs_updated_by_user_id'),
                    'hs_user_ids_of_all_notification_followers': props.get('hs_user_ids_of_all_notification_followers'),
                    'hs_user_ids_of_all_notification_unfollowers': props.get('hs_user_ids_of_all_notification_unfollowers'),
                    'hs_user_ids_of_all_owners': props.get('hs_user_ids_of_all_owners'),
                    'hs_was_imported': props.get('hs_was_imported') == 'true' if props.get('hs_was_imported') else None,
                }

                if record_id in existing_divisions:
                    # Update existing division
                    division_obj = existing_divisions[record_id]
                    
                    # Only update changed fields
                    changed = False
                    for field, new_value in division_data.items():
                        current_value = getattr(division_obj, field, None)
                        if self._values_differ(current_value, new_value):
                            setattr(division_obj, field, new_value)
                            changed = True
                    
                    if changed:
                        to_update.append(division_obj)
                else:
                    # Create new division
                    division_obj = Hubspot_Division(id=record_id, **division_data)
                    to_create.append(division_obj)
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing division {division.get('id')}: {str(e)}"))
                continue
        
        # Save to database with transaction
        try:
            with transaction.atomic():
                if to_create:
                    Hubspot_Division.objects.bulk_create(to_create, batch_size=50)
                    created = len(to_create)
                    self.stdout.write(f"Created {created} new divisions")
                
                if to_update:
                    Hubspot_Division.objects.bulk_update(to_update, [
                        'division_name', 'division_label', 'division_code', 'status', 'region',
                        'manager_name', 'manager_email', 'phone', 'address1', 'address2',
                        'city', 'state', 'zip', 'hs_createdate', 'hs_lastmodifieddate',
                        'hs_pipeline', 'hs_pipeline_stage', 'hs_object_id'
                    ], batch_size=50)
                    updated = len(to_update)
                    self.stdout.write(f"Updated {updated} existing divisions")
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error saving divisions: {str(e)}"))
            # Fall back to individual saves
            for obj in to_create:
                try:
                    obj.save()
                    created += 1
                except Exception as save_error:
                    self.stdout.write(self.style.ERROR(f"Error saving division {obj.id}: {str(save_error)}"))
            
            for obj in to_update:
                try:
                    obj.save()
                    updated += 1
                except Exception as save_error:
                    self.stdout.write(self.style.ERROR(f"Error updating division {obj.id}: {str(save_error)}"))
        
        return created, updated
    
    def get_last_sync(self, endpoint):
        """Get the last sync time for divisions."""
        try:
            history = Hubspot_SyncHistory.objects.get(endpoint=endpoint)
            return history.last_synced_at
        except Hubspot_SyncHistory.DoesNotExist:
            return None

    def update_last_sync(self, endpoint):
        """Update the last sync time for divisions."""
        history, _ = Hubspot_SyncHistory.objects.get_or_create(endpoint=endpoint)
        history.last_synced_at = timezone.now()
        history.save()
    
    def _parse_datetime(self, value):
        """Parse a datetime string into a datetime object."""
        if not value:
            return None
            
        try:
            # HubSpot often uses milliseconds since epoch
            if isinstance(value, str) and value.isdigit():
                timestamp = int(value) / 1000
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            
            # Try parsing as ISO format
            if isinstance(value, str):
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
                
            return value
        except (ValueError, TypeError):
            logger.warning(f"Could not parse datetime: {value}")
            return None
    
    def _values_differ(self, current, new):
        """Check if two values are different, handling None/null cases."""
        # Handle None cases
        if current is None and new is None:
            return False
        if current is None or new is None:
            return True
        
        # Handle datetime comparisons (timezone-aware)
        if isinstance(current, datetime) and isinstance(new, datetime):
            return current != new
        
        # Handle string comparisons (strip whitespace)
        if isinstance(current, str) and isinstance(new, str):
            return current.strip() != new.strip()
        
        # Default comparison
        return current != new
