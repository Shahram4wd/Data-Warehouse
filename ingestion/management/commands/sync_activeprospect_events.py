import asyncio
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async
from ingestion.models import ActiveProspect_Event, ActiveProspect_SyncHistory
from ingestion.activeprospect.activeprospect_client import ActiveProspectClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
BATCH_SIZE = 100


class Command(BaseCommand):
    help = "Sync events from ActiveProspect LeadConduit API"

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
            "--limit",
            type=int,
            default=1000,
            help="Maximum number of events to process per batch (max 1000)"
        )
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Number of days back to sync (default: 7, ignored if using incremental sync)"
        )
        parser.add_argument(
            "--event-type",
            type=str,
            choices=["source", "recipient", "filter", "feedback-received", "feedback-sent"],
            help="Filter by event type"
        )

    def handle(self, *args, **options):
        """Main command handler."""
        try:
            # Configure logging level
            if options.get("debug"):
                logging.getLogger().setLevel(logging.DEBUG)
                logging.getLogger("activeprospect_client").setLevel(logging.DEBUG)

            # Extract options
            full_sync = options.get("full", False)
            limit = min(options.get("limit", 1000), 1000)
            days = options.get("days", 7)
            event_type = options.get("event_type")

            self.stdout.write("Starting ActiveProspect events sync...")

            # Run the async sync process
            total_processed = asyncio.run(self.sync_events(
                full_sync=full_sync,
                limit=limit,
                days=days,
                event_type=event_type
            ))

            self.stdout.write(
                self.style.SUCCESS(
                    f"ActiveProspect events sync complete. Processed {total_processed} events total."
                )
            )

        except Exception as e:
            logger.exception("Error during ActiveProspect events sync")
            raise CommandError(f"Sync failed: {str(e)}")

    async def sync_events(self, full_sync=False, limit=1000, days=7, event_type=None):
        """Sync events from ActiveProspect API."""
        client = ActiveProspectClient()
        
        # Get the last sync time
        endpoint = f"events{'-' + event_type if event_type else ''}"
        
        if full_sync:
            # Use days parameter for full sync
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            self.stdout.write(f"Performing full sync for last {days} days")
        else:
            try:
                sync_history = await sync_to_async(ActiveProspect_SyncHistory.objects.get)(endpoint=endpoint)
                start_date = sync_history.last_synced_at.replace(tzinfo=None)
                end_date = datetime.now()
                self.stdout.write(f"Performing delta sync since {start_date}")
            except ActiveProspect_SyncHistory.DoesNotExist:
                # First time sync - get last 7 days
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                self.stdout.write("No previous sync found, performing initial sync for last 7 days")

        # Fetch events from API
        all_events = await self.fetch_events_from_api(
            client, start_date, end_date, limit, event_type
        )
        
        if all_events:
            # Process the events
            self.stdout.write("Processing events...")
            await self.process_events_batch(all_events)
        else:
            self.stdout.write("No events retrieved from API")

        # Update sync history
        await self.update_sync_history(endpoint, len(all_events))
        
        return len(all_events)

    async def fetch_events_from_api(self, client, start_date, end_date, limit, event_type):
        """Fetch events from ActiveProspect API with pagination"""
        self.stdout.write("Starting to fetch events from ActiveProspect...")
        self.stdout.write(f"Date range: {start_date} to {end_date}")
        self.stdout.write(f"Limit per request: {limit}")
        
        all_events = []
        after_id = None
        page = 1
        
        while True:
            self.stdout.write(f"Fetching batch {page}...")
            
            try:
                result = await client.get_events(
                    limit=limit,
                    start=start_date,
                    end=end_date,
                    after_id=after_id,
                    event_type=event_type
                )
                
                events_data = result.get('data', [])
                
                if not events_data:
                    self.stdout.write("No more events found")
                    break
                
                all_events.extend(events_data)
                self.stdout.write(f"Retrieved {len(events_data)} events")
                
                # Check if we have more data (use the last event ID for pagination)
                if len(events_data) < limit:
                    self.stdout.write("Reached end of data")
                    break
                    
                # Use the last event ID for next page
                after_id = events_data[-1].get('id')
                page += 1
                
            except Exception as e:
                logger.error(f"Error fetching events batch {page}: {str(e)}")
                break
        
        self.stdout.write(f"Retrieved {len(all_events)} events total")
        return all_events

    async def process_events_batch(self, events_data):
        """Process a batch of events and save to database."""
        self.stdout.write(f"Processing {len(events_data)} events...")
        
        # Get list of event IDs to check what already exists
        event_ids = [str(event_data.get('id')) for event_data in events_data if event_data.get('id')]
        
        # Get existing events
        existing_events = {
            event.id: event 
            for event in await sync_to_async(list)(ActiveProspect_Event.objects.filter(id__in=event_ids))
        }

        events_to_create = []
        events_to_update = []

        for event_data in events_data:
            try:
                event_id = event_data.get('id')
                if not event_id:
                    continue

                # Parse datetime fields
                expires_at = self.parse_datetime(event_data.get('expires_at'))

                # Extract request/response data
                request_data = event_data.get('request', {})
                response_data = event_data.get('response', {})

                # Prepare event fields
                event_fields = {
                    'outcome': event_data.get('outcome'),
                    'reason': event_data.get('reason'),
                    'event_type': event_data.get('type'),
                    'host': event_data.get('host'),
                    'start_timestamp': event_data.get('start_timestamp'),
                    'end_timestamp': event_data.get('end_timestamp'),
                    'ms': event_data.get('ms'),
                    'wait_ms': event_data.get('wait_ms'),
                    'overhead_ms': event_data.get('overhead_ms'),
                    'lag_ms': event_data.get('lag_ms'),
                    'total_ms': event_data.get('total_ms'),
                    'handler_version': event_data.get('handler_version'),
                    'version': event_data.get('version'),
                    'module_id': event_data.get('module_id'),
                    'package_version': event_data.get('package_version'),
                    'step_id': event_data.get('step_id'),
                    'step_count': event_data.get('step_count'),
                    'cap_reached': event_data.get('cap_reached', False),
                    'ping_limit_reached': event_data.get('ping_limit_reached', False),
                    'cost': event_data.get('cost'),
                    'purchase_price': event_data.get('purchase_price'),
                    'sale_price': event_data.get('sale_price'),
                    'revenue': event_data.get('revenue'),
                    'vars': event_data.get('vars'),
                    'appended': event_data.get('appended'),
                    'firehose': event_data.get('firehose'),
                    'flow_ping_limits': event_data.get('flow_ping_limits'),
                    'source_ping_limits': event_data.get('source_ping_limits'),
                    'acceptance_criteria': event_data.get('acceptance_criteria'),
                    'caps': event_data.get('caps'),
                    'request_method': request_data.get('method'),
                    'request_uri': request_data.get('uri'),
                    'request_version': request_data.get('version'),
                    'request_headers': request_data.get('headers'),
                    'request_body': request_data.get('body'),
                    'request_timestamp': request_data.get('timestamp'),
                    'response_status': response_data.get('status'),
                    'response_status_text': response_data.get('status_text'),
                    'response_version': response_data.get('version'),
                    'response_headers': response_data.get('headers'),
                    'response_body': response_data.get('body'),
                    'response_timestamp': response_data.get('timestamp'),
                    'expires_at': expires_at,
                }

                if event_id in existing_events:
                    # Update existing event
                    event = existing_events[event_id]
                    for field, value in event_fields.items():
                        setattr(event, field, value)
                    events_to_update.append(event)
                else:
                    # Create new event
                    event_fields['id'] = event_id
                    events_to_create.append(ActiveProspect_Event(**event_fields))

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error processing event {event_data.get('id', 'unknown')}: {str(e)}"))
                continue

        # Bulk save to database
        created, updated = await self.save_events(events_to_create, events_to_update)
        self.stdout.write(f"Created {created} events, updated {updated} events")

    async def save_events(self, events_to_create, events_to_update):
        """Save events to database with error handling."""
        try:
            def save_events_sync():
                with transaction.atomic():
                    created_count = 0
                    updated_count = 0
                    
                    if events_to_create:
                        created_before = ActiveProspect_Event.objects.count()
                        ActiveProspect_Event.objects.bulk_create(
                            events_to_create, 
                            batch_size=BATCH_SIZE,
                            ignore_conflicts=True
                        )
                        created_after = ActiveProspect_Event.objects.count()
                        created_count = created_after - created_before

                    if events_to_update:
                        updated_count = len(events_to_update)
                        update_fields = [
                            'outcome', 'reason', 'event_type', 'host', 'start_timestamp', 'end_timestamp',
                            'ms', 'wait_ms', 'overhead_ms', 'lag_ms', 'total_ms', 'handler_version', 'version',
                            'module_id', 'package_version', 'step_id', 'step_count', 'cap_reached', 'ping_limit_reached',
                            'cost', 'purchase_price', 'sale_price', 'revenue', 'vars', 'appended', 'firehose',
                            'flow_ping_limits', 'source_ping_limits', 'acceptance_criteria', 'caps',
                            'request_method', 'request_uri', 'request_version', 'request_headers', 'request_body',
                            'request_timestamp', 'response_status', 'response_status_text', 'response_version',
                            'response_headers', 'response_body', 'response_timestamp', 'expires_at'
                        ]
                        ActiveProspect_Event.objects.bulk_update(
                            events_to_update,
                            update_fields,
                            batch_size=BATCH_SIZE
                        )
                    
                    return created_count, updated_count
            
            created_count, updated_count = await sync_to_async(save_events_sync)()

        except Exception as e:
            logger.error(f"Error saving events to database: {str(e)}")
            raise

        return created_count, updated_count

    def parse_datetime(self, datetime_str):
        """Parse datetime string from API response."""
        if not datetime_str:
            return None
        
        try:
            # ActiveProspect uses ISO format
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return timezone.make_aware(dt, timezone=timezone.utc)
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Error parsing datetime {datetime_str}: {str(e)}"))
            return None

    async def update_sync_history(self, endpoint, records_processed):
        """Update the sync history record."""
        try:
            def update_sync_history_sync():
                sync_history, created = ActiveProspect_SyncHistory.objects.get_or_create(
                    endpoint=endpoint,
                    defaults={
                        'last_synced_at': timezone.now(),
                        'total_records': records_processed,
                        'success_count': records_processed,
                        'error_count': 0
                    }
                )
                
                if not created:
                    sync_history.last_synced_at = timezone.now()
                    sync_history.total_records = records_processed
                    sync_history.success_count = records_processed
                    sync_history.error_count = 0
                    sync_history.save()
                
                return sync_history
            
            await sync_to_async(update_sync_history_sync)()
            
        except Exception as e:
            logger.error(f"Error updating sync history: {str(e)}")
