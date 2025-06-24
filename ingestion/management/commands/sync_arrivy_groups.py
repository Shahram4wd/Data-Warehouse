import asyncio
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async
from ingestion.models.arrivy import Arrivy_Group, Arrivy_SyncHistory
from ingestion.arrivy.arrivy_client import ArrivyClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
BATCH_SIZE = 100

class Command(BaseCommand):
    help = "Sync groups/locations from Arrivy API using official groups endpoint"

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform a full sync instead of incremental sync"
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
            "--lastmodifieddate",
            type=str,
            help="Filter records modified after this date (YYYY-MM-DD format)"
        )

    def handle(self, *args, **options):
        """Main command handler."""
        try:
            # Configure logging level
            if options.get("debug"):
                logging.getLogger().setLevel(logging.DEBUG)
                logging.getLogger("arrivy_client").setLevel(logging.DEBUG)

            # Extract options
            full_sync = options.get("full", False)
            max_pages = options.get("pages", 0)
            lastmodifieddate = options.get("lastmodifieddate")

            self.stdout.write("Starting Arrivy groups sync...")

            # Run the async sync process
            total_processed = asyncio.run(self.sync_groups(
                full_sync=full_sync,
                max_pages=max_pages,
                lastmodifieddate=lastmodifieddate
            ))

            self.stdout.write(
                self.style.SUCCESS(
                    f"Arrivy groups sync complete. Processed {total_processed} groups total."
                )
            )

        except Exception as e:
            logger.exception("Error during Arrivy groups sync")
            raise CommandError(f"Sync failed: {str(e)}")

    async def sync_groups(self, full_sync=False, max_pages=0, lastmodifieddate=None):
        """Sync groups from Arrivy API."""
        client = ArrivyClient()
        
        # Get the last sync time
        sync_type = "groups"
        
        # Priority: 1) --lastmodifieddate parameter, 2) database last sync, 3) full sync
        if lastmodifieddate:
            try:
                last_sync = datetime.strptime(lastmodifieddate, "%Y-%m-%d")
                last_sync = timezone.make_aware(last_sync)
                self.stdout.write(f"Using provided lastmodifieddate filter: {lastmodifieddate}")
            except ValueError:
                raise CommandError("Invalid date format. Use YYYY-MM-DD")
        elif not full_sync:
            try:
                sync_history = await sync_to_async(Arrivy_SyncHistory.objects.get)(sync_type=sync_type)
                last_sync = sync_history.last_synced_at
                self.stdout.write(f"Performing delta sync since {last_sync}")
            except Arrivy_SyncHistory.DoesNotExist:
                last_sync = None
                self.stdout.write("No previous sync found, performing full sync")
        else:
            last_sync = None
            self.stdout.write("Performing full sync")

        # Fetch groups from API
        all_groups = await self.fetch_groups_from_api(client, last_sync, max_pages)
        
        if all_groups:
            # Process the groups in batches
            self.stdout.write("Processing final batch...")
            await self.process_groups_batch(all_groups)
        else:
            self.stdout.write("No groups retrieved from API")

        # Update sync history
        await self.update_sync_history(sync_type, len(all_groups))
        
        return len(all_groups)

    async def fetch_groups_from_api(self, client, last_sync, max_pages):
        """Fetch all groups from Arrivy API."""
        self.stdout.write("Starting to fetch groups from Arrivy...")
        self.stdout.write(f"Using batch size: {BATCH_SIZE}")
        
        all_groups = []
        page = 1
        
        while True:
            self.stdout.write(f"Fetching page {page}...")
            
            try:
                result = await client.get_groups(
                    page_size=BATCH_SIZE,
                    page=page,
                    last_sync=last_sync
                )
                
                groups_data = result.get('data', [])
                pagination = result.get('pagination')
                
                if not groups_data:
                    self.stdout.write("No more groups found")
                    break
                
                all_groups.extend(groups_data)
                self.stdout.write(f"Retrieved {len(groups_data)} groups")
                
                # Check if we should continue
                if max_pages and page >= max_pages:
                    self.stdout.write(f"Reached maximum pages limit: {max_pages}")
                    break
                
                # Check pagination
                if pagination and not pagination.get('has_next', False):
                    self.stdout.write("No more pages available")
                    break
                
                page += 1
                
            except Exception as e:
                logger.error(f"Error fetching groups page {page}: {str(e)}")
                break
        
        self.stdout.write(f"Retrieved {len(all_groups)} groups")
        return all_groups

    async def process_groups_batch(self, groups_data):
        """Process a batch of groups and save to database."""
        self.stdout.write(f"Processing {len(groups_data)} groups...")
        
        # Get list of group IDs to check what already exists
        group_ids = [str(group_data.get('id')) for group_data in groups_data if group_data.get('id')]
        
        # Get existing groups
        existing_groups = {
            group.id: group 
            for group in await sync_to_async(list)(Arrivy_Group.objects.filter(id__in=group_ids))
        }

        groups_to_create = []
        groups_to_update = []

        for group_data in groups_data:
            try:
                group_id = group_data.get('id')
                if not group_id:
                    continue

                # Parse datetime fields
                created_time = self.parse_datetime(group_data.get('created'))
                updated_time = self.parse_datetime(group_data.get('updated'))

                # Prepare group fields
                group_fields = {
                    'url_safe_id': group_data.get('url_safe_id'),
                    'owner': group_data.get('owner'),
                    'name': group_data.get('name'),
                    'description': group_data.get('description'),
                    'email': group_data.get('email'),
                    'phone': group_data.get('phone'),
                    'mobile_number': group_data.get('mobile_number'),
                    'website': group_data.get('website'),
                    'emergency': group_data.get('emergency'),
                    'address_line_1': group_data.get('address_line_1'),
                    'address_line_2': group_data.get('address_line_2'),
                    'complete_address': group_data.get('complete_address'),
                    'city': group_data.get('city'),
                    'state': group_data.get('state'),
                    'country': group_data.get('country'),
                    'zipcode': group_data.get('zipcode'),
                    'exact_location': group_data.get('exact_location'),
                    'use_lat_lng_address': group_data.get('use_lat_lng_address', False),
                    'is_address_geo_coded': group_data.get('is_address_geo_coded', False),
                    'timezone': group_data.get('timezone'),
                    'image_id': group_data.get('image_id'),
                    'image_path': group_data.get('image_path'),
                    'is_default': group_data.get('is_default', False),
                    'is_disabled': group_data.get('is_disabled', False),
                    'is_implicit': group_data.get('is_implicit', False),
                    'social_links': group_data.get('social_links'),
                    'additional_addresses': group_data.get('additional_addresses'),
                    'territory_ids': group_data.get('territory_ids'),
                    'extra_fields': group_data.get('extra_fields'),
                    'created_by': group_data.get('created_by'),
                    'created_time': created_time,
                    'updated_time': updated_time,
                }

                if group_id in existing_groups:
                    # Update existing group
                    group = existing_groups[group_id]
                    for field, value in group_fields.items():
                        setattr(group, field, value)
                    groups_to_update.append(group)
                else:
                    # Create new group
                    group_fields['id'] = group_id
                    groups_to_create.append(Arrivy_Group(**group_fields))

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error processing group {group_data.get('id', 'unknown')}: {str(e)}"))
                continue

        # Bulk save to database
        created, updated = await self.save_groups(groups_to_create, groups_to_update)
        self.stdout.write(f"Created {created} groups, updated {updated} groups")

    async def save_groups(self, groups_to_create, groups_to_update):
        """Save groups to database with error handling."""
        try:
            def save_groups_sync():
                with transaction.atomic():
                    created_count = 0
                    updated_count = 0
                    
                    if groups_to_create:
                        created_before = Arrivy_Group.objects.count()
                        Arrivy_Group.objects.bulk_create(
                            groups_to_create, 
                            batch_size=BATCH_SIZE,
                            ignore_conflicts=True
                        )
                        created_after = Arrivy_Group.objects.count()
                        created_count = created_after - created_before

                    if groups_to_update:
                        updated_count = len(groups_to_update)
                        Arrivy_Group.objects.bulk_update(
                            groups_to_update,
                            [
                                'url_safe_id', 'owner', 'name', 'description', 'email', 'phone',
                                'mobile_number', 'website', 'emergency', 'address_line_1', 'address_line_2',
                                'complete_address', 'city', 'state', 'country', 'zipcode', 'exact_location',
                                'use_lat_lng_address', 'is_address_geo_coded', 'timezone', 'image_id',
                                'image_path', 'is_default', 'is_disabled', 'is_implicit', 'social_links',
                                'additional_addresses', 'territory_ids', 'extra_fields', 'created_by',
                                'created_time', 'updated_time'
                            ],
                            batch_size=BATCH_SIZE
                        )
                    
                    return created_count, updated_count
            
            created_count, updated_count = await sync_to_async(save_groups_sync)()

        except Exception as e:
            logger.error(f"Error saving groups to database: {str(e)}")
            raise

        return created_count, updated_count

    def parse_datetime(self, datetime_str):
        """Parse datetime string from API response."""
        if not datetime_str:
            return None
        
        try:
            # Try different datetime formats
            for fmt in [
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S"
            ]:
                try:
                    dt = datetime.strptime(datetime_str, fmt)
                    return timezone.make_aware(dt)
                except ValueError:
                    continue
            
            self.stdout.write(self.style.WARNING(f"Could not parse datetime: {datetime_str}"))
            return None
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Error parsing datetime {datetime_str}: {str(e)}"))
            return None

    async def update_sync_history(self, sync_type, records_processed):
        """Update the sync history record."""
        try:
            def update_sync_history_sync():
                sync_history, created = Arrivy_SyncHistory.objects.get_or_create(
                    sync_type=sync_type,
                    defaults={
                        'last_synced_at': timezone.now(),
                    }
                )
                
                if not created:
                    sync_history.last_synced_at = timezone.now()
                    sync_history.save()
                
                return sync_history
            
            await sync_to_async(update_sync_history_sync)()
            
        except Exception as e:
            logger.error(f"Error updating sync history: {str(e)}")
