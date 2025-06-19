import asyncio
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async
from ingestion.models import Arrivy_Entity, Arrivy_SyncHistory
from ingestion.arrivy.arrivy_client import ArrivyClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
BATCH_SIZE = 100

class Command(BaseCommand):
    help = "Sync individual crew members (entities) from Arrivy API"

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

            self.stdout.write("Starting Arrivy entities sync...")

            # Run the async sync process
            total_processed = asyncio.run(self.sync_entities(
                full_sync=full_sync,
                max_pages=max_pages,
                lastmodifieddate=lastmodifieddate
            ))

            self.stdout.write(
                self.style.SUCCESS(
                    f"Arrivy entities sync complete. Processed {total_processed} entities total."
                )
            )

        except Exception as e:
            logger.exception("Error during Arrivy entities sync")
            raise CommandError(f"Sync failed: {str(e)}")

    async def sync_entities(self, full_sync=False, max_pages=0, lastmodifieddate=None):
        """Sync entities from Arrivy API."""
        client = ArrivyClient()
        
        # Get the last sync time
        endpoint = "entities"
        
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
                sync_history = await sync_to_async(Arrivy_SyncHistory.objects.get)(endpoint=endpoint)
                last_sync = sync_history.last_synced_at
                self.stdout.write(f"Performing delta sync since {last_sync}")
            except Arrivy_SyncHistory.DoesNotExist:
                last_sync = None
                self.stdout.write("No previous sync found, performing full sync")
        else:
            last_sync = None
            self.stdout.write("Performing full sync")        # Fetch entities from API
        all_entities = await self.fetch_entities_from_api(client, last_sync, max_pages)
        
        if all_entities:
            # Process the entities in batches
            self.stdout.write("Processing final batch...")
            await self.process_entities_batch(all_entities)
        else:
            self.stdout.write("No entities retrieved from API")

        # Update sync history
        await self.update_sync_history(endpoint, len(all_entities))
        
        return len(all_entities)

    async def fetch_entities_from_api(self, client, last_sync, max_pages):
        """Fetch all entities from Arrivy API."""
        self.stdout.write("Starting to fetch entities from Arrivy...")
        self.stdout.write(f"Using batch size: {BATCH_SIZE}")
        
        all_entities = []
        page = 1
        
        while True:
            self.stdout.write(f"Fetching page {page}...")
            
            try:
                result = await client.get_entities(
                    page_size=BATCH_SIZE,
                    page=page,
                    last_sync=last_sync
                )
                
                entities_data = result.get('data', [])
                pagination = result.get('pagination')
                
                if not entities_data:
                    self.stdout.write("No more entities found")
                    break
                
                all_entities.extend(entities_data)
                self.stdout.write(f"Retrieved {len(entities_data)} entities")
                
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
                logger.error(f"Error fetching entities page {page}: {str(e)}")
                break
        
        self.stdout.write(f"Retrieved {len(all_entities)} entities")
        return all_entities

    async def process_entities_batch(self, entities_data):
        """Process a batch of entities and save to database."""
        self.stdout.write(f"Processing {len(entities_data)} entities...")
        
        # Get list of entity IDs to check what already exists
        entity_ids = [str(entity_data.get('id')) for entity_data in entities_data if entity_data.get('id')]
          # Get existing entities
        existing_entities = {
            entity.id: entity 
            for entity in await sync_to_async(list)(Arrivy_Entity.objects.filter(id__in=entity_ids))
        }

        entities_to_create = []
        entities_to_update = []

        for entity_data in entities_data:
            try:
                entity_id = entity_data.get('id')
                if not entity_id:
                    continue

                # Parse datetime fields
                created_time = self.parse_datetime(entity_data.get('created'))
                updated_time = self.parse_datetime(entity_data.get('updated'))
                joined_datetime = self.parse_datetime(entity_data.get('joined_datetime'))

                # Prepare entity fields
                entity_fields = {
                    'name': entity_data.get('name'),
                    'username': entity_data.get('username'),
                    'type': entity_data.get('type'),
                    'external_id': entity_data.get('external_id'),
                    'external_type': entity_data.get('external_type'),
                    'email': entity_data.get('email'),
                    'phone': entity_data.get('phone'),
                    'image_id': entity_data.get('image_id'),
                    'image_path': entity_data.get('image_path'),
                    'color': entity_data.get('color'),
                    'url_safe_id': entity_data.get('url_safe_id'),
                    'is_active': entity_data.get('is_active', True),
                    'is_disabled': entity_data.get('is_disabled', False),
                    'is_default': entity_data.get('is_default', False),
                    'user_type': entity_data.get('user_type'),
                    'invite_status': entity_data.get('invite_status'),
                    'group_id': entity_data.get('group_id'),
                    'owner': entity_data.get('owner'),
                    'additional_group_ids': entity_data.get('additional_group_ids'),
                    'address_line_1': entity_data.get('address_line_1'),
                    'address_line_2': entity_data.get('address_line_2'),
                    'city': entity_data.get('city'),
                    'state': entity_data.get('state'),
                    'country': entity_data.get('country'),
                    'zipcode': entity_data.get('zipcode'),
                    'complete_address': entity_data.get('complete_address'),
                    'exact_location': entity_data.get('exact_location'),
                    'is_address_geo_coded': entity_data.get('is_address_geo_coded', False),
                    'use_lat_lng_address': entity_data.get('use_lat_lng_address', False),
                    'allow_login_in_kiosk_mode_only': entity_data.get('allow_login_in_kiosk_mode_only', False),
                    'can_turnoff_location': entity_data.get('can_turnoff_location', True),
                    'can_view_customers_of_all_groups': entity_data.get('can_view_customers_of_all_groups', False),
                    'is_status_priority_notifications_disabled': entity_data.get('is_status_priority_notifications_disabled', False),
                    'is_included_in_billing': entity_data.get('is_included_in_billing', True),
                    'force_stop_billing': entity_data.get('force_stop_billing', False),
                    'skill_ids': entity_data.get('skill_ids'),
                    'skill_details': entity_data.get('skill_details'),
                    'details': entity_data.get('details'),
                    'extra_fields': entity_data.get('extra_fields'),
                    'visible_bookings': entity_data.get('visible_bookings'),
                    'visible_routing_forms': entity_data.get('visible_routing_forms'),
                    'notifications': entity_data.get('notifications'),
                    'allow_status_notifications': entity_data.get('allow_status_notifications'),
                    'permission_groups': entity_data.get('permission_groups'),
                    'template_id': entity_data.get('template_id'),
                    'template_extra_fields': entity_data.get('template_extra_fields'),
                    'created_by': entity_data.get('created_by'),
                    'created_by_user': entity_data.get('created_by_user'),
                    'created_time': created_time,
                    'updated_by': entity_data.get('updated_by'),
                    'updated_by_user': entity_data.get('updated_by_user'),
                    'updated_time': updated_time,
                    'joined_datetime': joined_datetime,
                    'last_reading': entity_data.get('lastreading'),
                    'okta_user_id': entity_data.get('okta_user_id'),
                }

                if entity_id in existing_entities:
                    # Update existing entity
                    entity = existing_entities[entity_id]
                    for field, value in entity_fields.items():
                        setattr(entity, field, value)
                    entities_to_update.append(entity)
                else:
                    # Create new entity
                    entity_fields['id'] = entity_id
                    entities_to_create.append(Arrivy_Entity(**entity_fields))

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error processing entity {entity_data.get('id', 'unknown')}: {str(e)}"))
                continue        # Bulk save to database
        created, updated = await self.save_entities(entities_to_create, entities_to_update)
        self.stdout.write(f"Created {created} entities, updated {updated} entities")

    async def save_entities(self, entities_to_create, entities_to_update):
        """Save entities to database with error handling."""
        try:
            def save_entities_sync():
                with transaction.atomic():
                    created_count = 0
                    updated_count = 0
                    
                    if entities_to_create:
                        created_before = Arrivy_Entity.objects.count()
                        Arrivy_Entity.objects.bulk_create(
                            entities_to_create, 
                            batch_size=BATCH_SIZE,
                            ignore_conflicts=True
                        )
                        created_after = Arrivy_Entity.objects.count()
                        created_count = created_after - created_before

                    if entities_to_update:
                        updated_count = len(entities_to_update)
                        Arrivy_Entity.objects.bulk_update(
                            entities_to_update,
                            [
                                'name', 'username', 'type', 'external_id', 'external_type',
                                'email', 'phone', 'image_id', 'image_path', 'color', 'url_safe_id',
                                'is_active', 'is_disabled', 'is_default', 'user_type', 'invite_status',
                                'group_id', 'owner', 'additional_group_ids',
                                'address_line_1', 'address_line_2', 'city', 'state', 'country', 'zipcode',
                                'complete_address', 'exact_location', 'is_address_geo_coded', 'use_lat_lng_address',
                                'allow_login_in_kiosk_mode_only', 'can_turnoff_location', 'can_view_customers_of_all_groups',
                                'is_status_priority_notifications_disabled', 'is_included_in_billing', 'force_stop_billing',
                                'skill_ids', 'skill_details', 'details', 'extra_fields', 'visible_bookings',
                                'visible_routing_forms', 'notifications', 'allow_status_notifications',
                                'permission_groups', 'template_id', 'template_extra_fields',
                                'created_by', 'created_by_user', 'created_time', 'updated_by', 'updated_by_user',
                                'updated_time', 'joined_datetime', 'last_reading', 'okta_user_id'
                            ],
                            batch_size=BATCH_SIZE
                        )
                    
                    return created_count, updated_count
            
            created_count, updated_count = await sync_to_async(save_entities_sync)()

        except Exception as e:
            logger.error(f"Error saving entities to database: {str(e)}")
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

    async def update_sync_history(self, endpoint, records_processed):
        """Update the sync history record."""
        try:
            def update_sync_history_sync():
                sync_history, created = Arrivy_SyncHistory.objects.get_or_create(
                    endpoint=endpoint,
                    defaults={
                        'last_synced_at': timezone.now(),
                        'records_processed': records_processed,
                        'status': 'SUCCESS'
                    }
                )
                
                if not created:
                    sync_history.last_synced_at = timezone.now()
                    sync_history.records_processed = records_processed
                    sync_history.status = 'SUCCESS'
                    sync_history.save()
                
                return sync_history
            
            await sync_to_async(update_sync_history_sync)()
            
        except Exception as e:
            logger.error(f"Error updating sync history: {str(e)}")
