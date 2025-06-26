from django.core.management.base import BaseCommand
from ingestion.leadconduit.leadconduit_client import LeadConduitClient
from ingestion.leadconduit.base_processor import BaseLeadConduitProcessor
from ingestion.models.leadconduit import LeadConduit_Event, LeadConduit_Lead
from django.db import transaction
from tqdm import tqdm
from datetime import datetime, timezone as tz
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand, BaseLeadConduitProcessor):
    help = "Sync events from LeadConduit API"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        BaseLeadConduitProcessor.__init__(self, 'events')

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='Maximum number of events to fetch (default: 1000)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days back to fetch events (default: 7)'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without saving to database'
        )
        parser.add_argument(
            '--update-leads',
            action='store_true',
            help='Also update/create lead records from event data'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        days_back = options.get('days', 7)
        start_date = options.get('start_date')
        end_date = options.get('end_date')
        dry_run = options.get('dry_run', False)
        update_leads = options.get('update_leads', False)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        self.stdout.write(self.style.SUCCESS("=== LEADCONDUIT EVENTS SYNC ==="))

        try:
            # Initialize client
            client = LeadConduitClient()
            
            # Parse date range
            end_dt = None
            start_dt = None
            
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=tz.utc)
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=tz.utc)
            elif not start_dt and days_back:
                from datetime import timedelta
                end_dt = end_dt or datetime.now(tz.utc)
                start_dt = end_dt - timedelta(days=days_back)

            self.stdout.write(f"📅 Date range: {start_dt} to {end_dt}")
            self.stdout.write(f"📊 Max events: {limit}")

            if not dry_run:
                sync_history = self.start_sync(
                    api_endpoint='/events',
                    query_params={
                        'limit': limit,
                        'start': start_dt.isoformat() if start_dt else None,
                        'end': end_dt.isoformat() if end_dt else None
                    }
                )

            # Fetch events
            self.stdout.write("Fetching events from LeadConduit...")
            
            # Fetch and process events in pages
            page_size = 1000
            total_fetched = 0
            created_count = 0
            updated_count = 0
            leads_created = 0
            leads_updated = 0

            for page_events in client.get_events_paginated(
                limit_per_page=page_size,
                max_total=limit,
                start=start_dt,
                end=end_dt
            ):
                if not page_events:
                    break

                # Handle case where page_events is a dictionary
                if isinstance(page_events, dict):
                    if 'data' in page_events:
                        page_events = page_events['data']
                    elif 'results' in page_events:
                        page_events = page_events['results']
                    elif 'items' in page_events:
                        page_events = page_events['items']
                    elif 'id' in page_events:
                        # Detected a single event record, wrap into list
                        logger.info(f"Single event record detected for page_events, wrapping into list: {page_events.get('id')}")
                        page_events = [page_events]
                    else:
                        logger.error(f"Unexpected dictionary format for page_events: {page_events}")
                        self.stdout.write(self.style.ERROR("Unexpected dictionary format for page_events. Skipping page."))
                        continue

                # Debug: Inspect the structure of page_events
                if not isinstance(page_events, list):
                    logger.error(f"Unexpected data format for page_events: {type(page_events)}")
                    self.stdout.write(self.style.ERROR("Unexpected data format for page_events. Skipping page."))
                    continue

                # Validate each event in page_events
                valid_events = []
                for event in page_events:
                    if not isinstance(event, dict):
                        logger.warning(f"Skipping invalid event: {event}")
                        continue
                    valid_events.append(event)

                if not valid_events:
                    self.stdout.write(self.style.WARNING("No valid events found on this page. Skipping."))
                    continue

                self.stdout.write(f"Processing page with {len(valid_events)} valid events...")

                # Get existing event IDs for bulk operations
                event_ids = [event['id'] for event in valid_events]
                existing_events = set(LeadConduit_Event.objects.filter(
                    id__in=event_ids
                ).values_list('id', flat=True))

                # Process in batches
                batch_size = 100
                for i in tqdm(range(0, len(valid_events), batch_size), desc="Processing batches"):
                    batch = valid_events[i:i + batch_size]

                    with transaction.atomic():
                        events_to_create = []
                        events_to_update = []

                        for event_data in batch:
                            event_id = event_data['id']

                            # Handle missing event_type
                            event_type = event_data.get('type', 'unknown')  # Default to 'unknown' if missing
                            if not event_type:
                                logger.warning(f"Missing event_type for event ID {event_data.get('id')}")
                                event_type = 'unknown'

                            # Parse event fields
                            parsed_event = {
                                'outcome': event_data.get('outcome', ''),
                                'reason': event_data.get('reason'),
                                'event_type': event_type,  # Use the default or provided value
                                'host': event_data.get('host'),
                                'start_timestamp': event_data.get('start_timestamp'),
                                'end_timestamp': event_data.get('end_timestamp'),
                                'expires_at': self.parse_iso_datetime(event_data.get('expires_at')),
                                'ms': event_data.get('ms'),
                                'wait_ms': event_data.get('wait_ms'),
                                'overhead_ms': event_data.get('overhead_ms'),
                                'lag_ms': event_data.get('lag_ms'),
                                'total_ms': event_data.get('total_ms'),
                                'vars_data': event_data.get('vars'),
                                'appended_data': event_data.get('appended'),
                                'handler_version': event_data.get('handler_version'),
                                'version': event_data.get('version'),
                                'package_version': event_data.get('package_version'),
                                'cap_reached': event_data.get('cap_reached', False),
                                'ping_limit_reached': event_data.get('ping_limit_reached', False),
                                'step_count': event_data.get('step_count'),
                                'module_id': event_data.get('module_id'),
                                'request_data': event_data.get('request'),
                                'response_data': event_data.get('response'),
                            }

                            if event_id in existing_events:
                                # Update existing
                                try:
                                    event_obj = LeadConduit_Event.objects.get(id=event_id)
                                    for field, value in parsed_event.items():
                                        setattr(event_obj, field, value)
                                    events_to_update.append(event_obj)
                                except LeadConduit_Event.DoesNotExist:
                                    # Create new if not found
                                    events_to_create.append(LeadConduit_Event(id=event_id, **parsed_event))
                            else:
                                # Create new
                                events_to_create.append(LeadConduit_Event(id=event_id, **parsed_event))

                        # Bulk operations
                        if events_to_create:
                            LeadConduit_Event.objects.bulk_create(events_to_create, ignore_conflicts=True)
                            created_count += len(events_to_create)

                        if events_to_update:
                            update_fields = ['outcome', 'reason', 'event_type', 'vars_data', 'appended_data',
                                             'start_timestamp', 'end_timestamp', 'ms', 'updated_at']
                            LeadConduit_Event.objects.bulk_update(events_to_update, update_fields)
                            updated_count += len(events_to_update)

                        # Process leads if requested
                        if update_leads:
                            lead_results = self.process_leads_from_events(batch)
                            leads_created += lead_results['created']
                            leads_updated += lead_results['updated']

                total_fetched += len(page_events)

            # Complete sync
            self.complete_sync(
                records_processed=total_fetched,
                records_created=created_count,
                records_updated=updated_count
            )

            # Show results
            self.stdout.write(self.style.SUCCESS("Sync completed successfully!"))
            self.stdout.write(f"📊 Events processed: {total_fetched}")
            self.stdout.write(f"✅ Events created: {created_count}")
            self.stdout.write(f"🔄 Events updated: {updated_count}")

            if update_leads:
                self.stdout.write(f"👤 Leads created: {leads_created}")
                self.stdout.write(f"👤 Leads updated: {leads_updated}")

        except Exception as e:
            error_msg = f"Sync failed: {str(e)}"
            if not dry_run:
                self.fail_sync(error_msg)
            self.stdout.write(self.style.ERROR(error_msg))
            raise

    def parse_event_data(self, event_data):
        """Parse event data into model fields"""
        return {
            'outcome': event_data.get('outcome', ''),
            'reason': event_data.get('reason'),
            'event_type': event_data.get('type', ''),
            'host': event_data.get('host'),
            'start_timestamp': event_data.get('start_timestamp'),
            'end_timestamp': event_data.get('end_timestamp'),
            'expires_at': self.parse_iso_datetime(event_data.get('expires_at')),
            'ms': event_data.get('ms'),
            'wait_ms': event_data.get('wait_ms'),
            'overhead_ms': event_data.get('overhead_ms'),
            'lag_ms': event_data.get('lag_ms'),
            'total_ms': event_data.get('total_ms'),
            'vars_data': event_data.get('vars'),
            'appended_data': event_data.get('appended'),
            'handler_version': event_data.get('handler_version'),
            'version': event_data.get('version'),
            'package_version': event_data.get('package_version'),
            'cap_reached': event_data.get('cap_reached', False),
            'ping_limit_reached': event_data.get('ping_limit_reached', False),
            'step_count': event_data.get('step_count'),
            'module_id': event_data.get('module_id'),
            'request_data': event_data.get('request'),
            'response_data': event_data.get('response'),
        }

    def process_leads_from_events(self, events_batch):
        """Extract and save lead data from events"""
        leads_created = 0
        leads_updated = 0
        
        for event_data in events_batch:
            lead_id = self.extract_lead_id(event_data)
            if not lead_id:
                continue
                
            lead_info = self.extract_lead_data(event_data)
            if not lead_info:
                continue

            # Update or create lead
            lead, created = LeadConduit_Lead.objects.update_or_create(
                lead_id=lead_id,
                defaults={
                    'first_name': lead_info.get('first_name'),
                    'last_name': lead_info.get('last_name'),
                    'email': self.clean_email(lead_info.get('email')),
                    'phone_1': self.clean_phone(lead_info.get('phone_1')),
                    'phone_2': self.clean_phone(lead_info.get('phone_2')),
                    'address_1': lead_info.get('address_1'),
                    'address_2': lead_info.get('address_2'),
                    'city': lead_info.get('city'),
                    'state': lead_info.get('state'),
                    'postal_code': lead_info.get('postal_code'),
                    'country': lead_info.get('country'),
                    'reference': lead_info.get('reference'),
                    'full_data': lead_info.get('full_data'),
                    'latest_event_id': event_data['id'],
                    'latest_outcome': event_data.get('outcome'),
                    'submission_timestamp': self.parse_timestamp(event_data.get('start_timestamp')),
                }
            )
            
            if created:
                leads_created += 1
            else:
                leads_updated += 1
        
        return {'created': leads_created, 'updated': leads_updated}

    def show_sample_events(self, events):
        """Show sample events for dry run"""
        self.stdout.write(self.style.SUCCESS("\nSample events that would be imported:"))
        self.stdout.write("-" * 80)
        
        for i, event in enumerate(events, 1):
            self.stdout.write(f"\nEvent {i}:")
            self.stdout.write(f"  ID: {event.get('id')}")
            self.stdout.write(f"  Type: {event.get('type')}")
            self.stdout.write(f"  Outcome: {event.get('outcome')}")
            self.stdout.write(f"  Timestamp: {event.get('start_timestamp')}")
            
            # Show lead data
            vars_data = event.get('vars', {})
            if vars_data:
                self.stdout.write("  Lead Variables:")
                for key, value in list(vars_data.items())[:3]:
                    self.stdout.write(f"    {key}: {value}")
            
        self.stdout.write("\n" + "-" * 80)
        self.stdout.write("Run without --dry-run to perform the actual import.")
