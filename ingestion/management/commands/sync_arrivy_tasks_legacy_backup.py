import asyncio
import logging
import time
from datetime import datetime

from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from ingestion.arrivy.arrivy_client import ArrivyClient
from ingestion.models.arrivy import Arrivy_Task, Arrivy_SyncHistory

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
BACKOFF_MULTIPLIER = 2

class Command(BaseCommand):
    help = "Sync tasks from Arrivy API"

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

    def handle(self, *args, **options):
        full_sync = options.get("full")
        max_pages = options.get("pages", 0)

        if not all([settings.ARRIVY_API_KEY, settings.ARRIVY_AUTH_KEY, settings.ARRIVY_API_URL]):
            raise CommandError("Arrivy API credentials are not properly configured in settings.")

        self.stdout.write(self.style.SUCCESS("Starting Arrivy tasks sync..."))        # Get the last sync time
        sync_type = "tasks"
        last_sync = None if full_sync else self.get_last_sync(sync_type)

        if last_sync:
            self.stdout.write(f"Performing delta sync since {last_sync}")
        else:
            self.stdout.write("Performing full sync")

        try:
            total_pages = 0
            failed_pages = []
            client = ArrivyClient()
            
            self.stdout.write("Starting to fetch tasks from Arrivy...")
            self.stdout.write(f"Using batch size: {BATCH_SIZE}")
            self.stdout.write(f"Retry settings: {MAX_RETRIES} retries, {RETRY_DELAY}s delay, {BACKOFF_MULTIPLIER}x backoff")
            
            page = 1
            has_next = True

            while has_next:
                if max_pages > 0 and total_pages >= max_pages:
                    self.stdout.write(f"Reached maximum page limit of {max_pages}")
                    break

                total_pages += 1

                page_result = self.fetch_page_with_retry(client, page, BATCH_SIZE, last_sync)

                if page_result is None:
                    # API call failed after retries
                    failed_pages.append(page)
                    self.stdout.write(self.style.WARNING(
                        f"Skipping page {page} due to API errors. Continuing with next page..."
                    ))
                    page += 1
                    continue

                if not page_result or not page_result.get('data'):
                    self.stdout.write("No more data to fetch")
                    break

                page_data = page_result['data']
                pagination = page_result.get('pagination', {})

                self.stdout.write(f"Retrieved {len(page_data)} tasks from page {page}")
                self.stdout.write(f"API response pagination: {pagination}")
                logger.debug(f"API response pagination: {pagination}")

                # Process and save this page immediately
                try:
                    self.process_tasks_batch(page_data)
                    self.stdout.write(f"Successfully processed page {page}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing page {page}: {str(e)}"))
                    logger.exception(f"Error processing page {page}")
                    failed_pages.append(page)

                # Check if there are more pages
                if pagination is None:
                    has_next = len(page_data) > 0
                else:
                    has_next = pagination.get('has_next', len(page_data) == BATCH_SIZE)
                page = pagination.get('next_page', page + 1) if pagination else page + 1

            # Update sync timestamp only if we processed at least some pages successfully
            if total_pages > len(failed_pages):
                self.update_last_sync(sync_type)

            # Summary
            successful_pages = total_pages - len(failed_pages)
            self.stdout.write(self.style.SUCCESS(
                f"Arrivy tasks sync complete. "
                f"Successfully processed: {successful_pages} pages. "
                f"Failed pages: {len(failed_pages)}"
            ))
            
            if failed_pages:
                self.stdout.write(self.style.WARNING(f"Failed pages: {failed_pages}"))
                logger.warning(f"Sync completed with failed pages: {failed_pages}")
            
            logger.info(f"Sync summary - Total: {total_pages}, Success: {successful_pages}, Failed: {len(failed_pages)}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Critical error in sync process: {str(e)}"))
            logger.exception("Critical error during Arrivy tasks sync")
            raise CommandError(f"Sync failed: {str(e)}")

    def process_tasks_batch(self, tasks_data):
        """Process a batch of tasks data."""
        if not tasks_data:
            return

        self.stdout.write(f"Processing {len(tasks_data)} tasks...")

        # Get existing tasks
        task_ids = [task.get('id') for task in tasks_data if task.get('id')]
        existing_tasks = {
            task.task_id: task
            for task in Arrivy_Task.objects.filter(task_id__in=task_ids)
        }

        tasks_to_create = []
        tasks_to_update = []

        for task_data in tasks_data:
            try:
                task_id = task_data.get('id')
                if not task_id:
                    continue                # Prepare task fields
                task_fields = {
                    'task_id': str(task_id),
                    'task_title': task_data.get('title', ''),
                    'first_name': task_data.get('customer_first_name'),
                    'last_name': task_data.get('customer_last_name'),
                    'email': task_data.get('customer_email'),
                    'mobile_number': task_data.get('customer_phone') or task_data.get('customer_mobile_number'),
                    'address': task_data.get('customer_address_line_1'),
                    'city': task_data.get('customer_city'),
                    'state': task_data.get('customer_state'),
                    'zipcode': task_data.get('customer_zipcode'),
                    'country': task_data.get('customer_country'),
                    'latitude': task_data.get('customer_exact_location', {}).get('lat') if task_data.get('customer_exact_location') else None,
                    'longitude': task_data.get('customer_exact_location', {}).get('lng') if task_data.get('customer_exact_location') else None,
                    'start_date': self.parse_date(task_data.get('start_datetime')),
                    'start_time': self.parse_time(task_data.get('start_datetime')),
                    'end_date': self.parse_date(task_data.get('end_datetime')),
                    'end_time': self.parse_time(task_data.get('end_datetime')),
                    'status': task_data.get('status'),
                    'timezone': task_data.get('start_datetime_timezone'),
                    'instructions': task_data.get('details'),
                    'created_on': self.parse_datetime(task_data.get('created')),
                    'external_id': task_data.get('external_id'),
                    'booking_id': str(task_data.get('booking_id')) if task_data.get('booking_id') else None,                    'customer_id': str(task_data.get('customer_id')) if task_data.get('customer_id') else None,
                    'duration': str(task_data.get('duration')) if task_data.get('duration') else None,
                    'unscheduled': task_data.get('unscheduled', False),
                    'complete': task_data.get('status') == 'COMPLETE',
                    'cancel': task_data.get('status') in ['CANCELLED', 'CANCELED'],
                    'start': task_data.get('status') == 'STARTED',
                    'template_extra_field_product_interest_primary': self.get_template_field(task_data, 'Product Interest Primary'),
                    'template_extra_field_product_interest_secondary': self.get_template_field(task_data, 'Product Interest Secondary'),
                    'template_extra_field_primary_source': self.get_template_field(task_data, 'Primary Source'),
                    'template_extra_field_secondary_source': self.get_template_field(task_data, 'Secondary Source'),
                    'customer_extra_fields': self.json_dumps(task_data.get('extra_fields')),
                    'task_extra_fields': self.json_dumps(task_data.get('template_extra_fields')),
                    'resource_extra_field': self.json_dumps(task_data.get('entities_data')),
                }

                if task_id in existing_tasks:
                    # Update existing task
                    task = existing_tasks[task_id]
                    for field, value in task_fields.items():
                        setattr(task, field, value)
                    tasks_to_update.append(task)
                else:
                    # Create new task
                    tasks_to_create.append(Arrivy_Task(**task_fields))

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error processing task {task_data.get('id', 'unknown')}: {str(e)}"))
                continue

        # Bulk save to database
        created, updated = self.save_tasks(tasks_to_create, tasks_to_update)
        self.stdout.write(f"Created {created} tasks, updated {updated} tasks")

    def save_tasks(self, tasks_to_create, tasks_to_update):
        """Save tasks to database with error handling."""
        created_count = 0
        updated_count = 0

        try:
            with transaction.atomic():
                if tasks_to_create:
                    Arrivy_Task.objects.bulk_create(tasks_to_create, batch_size=BATCH_SIZE, ignore_conflicts=True)
                    created_count = len(tasks_to_create)
                    
                if tasks_to_update:
                    update_fields = [
                        'task_title', 'first_name', 'last_name', 'email', 'mobile_number', 'address',
                        'city', 'state', 'zipcode', 'country', 'latitude', 'longitude', 'start_date',
                        'start_time', 'end_date', 'end_time', 'status', 'timezone', 'instructions', 
                        'created_on', 'external_id', 'booking_id', 'customer_id', 'duration', 'unscheduled',
                        'complete', 'cancel', 'start', 'template_extra_field_product_interest_primary',
                        'template_extra_field_product_interest_secondary', 'template_extra_field_primary_source',
                        'template_extra_field_secondary_source', 'customer_extra_fields', 'task_extra_fields',
                        'resource_extra_field'
                    ]
                    Arrivy_Task.objects.bulk_update(tasks_to_update, update_fields, batch_size=BATCH_SIZE)
                    updated_count = len(tasks_to_update)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error saving tasks: {str(e)}"))
            logger.exception("Error saving tasks to database")
            raise

        return created_count, updated_count

    def get_last_sync(self, sync_type):
        """Get the last sync time for tasks."""
        try:
            history = Arrivy_SyncHistory.objects.get(sync_type=sync_type)
            return history.last_synced_at
        except Arrivy_SyncHistory.DoesNotExist:
            return None

    def update_last_sync(self, sync_type):
        """Update the last sync time for tasks."""
        now = timezone.now()
        history, created = Arrivy_SyncHistory.objects.get_or_create(
            sync_type=sync_type,
            defaults={'last_synced_at': now}
        )
        if not created:
            history.last_synced_at = now
            history.save()

    def parse_datetime(self, datetime_str):
        """Parse datetime string from API response and ensure it is timezone-aware if USE_TZ is True."""
        if not datetime_str:
            return None
        try:
            # Parse ISO format datetime string
            if 'T' in datetime_str:
                # Remove timezone suffix if present and parse
                dt_str = datetime_str.split('+')[0].split('-')[0] if '+' in datetime_str or datetime_str.count('-') > 2 else datetime_str
                dt = datetime.fromisoformat(dt_str.replace('Z', ''))
                # Make timezone-aware if needed
                if dt and timezone.is_naive(dt) and settings.USE_TZ:
                    return timezone.make_aware(dt, timezone=timezone.utc)
                return dt
            return None
        except (ValueError, AttributeError):
            return None

    def parse_date(self, datetime_str):
        """Parse date from datetime string."""
        if not datetime_str:
            return None
        try:
            dt = self.parse_datetime(datetime_str)
            return dt.date() if dt else None
        except (ValueError, AttributeError):
            return None

    def parse_time(self, datetime_str):
        """Parse time from datetime string."""
        if not datetime_str:
            return None
        try:
            dt = self.parse_datetime(datetime_str)
            return dt.time() if dt else None
        except (ValueError, AttributeError):
            return None

    def get_template_field(self, task_data, field_name):
        """Extract value from template_extra_fields by field name."""
        template_fields = task_data.get('template_extra_fields', [])
        if not template_fields:
            return None
        
        for field in template_fields:
            if field.get('name') == field_name:
                return field.get('value')
        return None

    def json_dumps(self, data):
        """Safely convert data to JSON string."""
        if not data:
            return None
        try:
            import json
            return json.dumps(data)
        except (TypeError, ValueError):
            return str(data) if data else None

    def fetch_page_with_retry(self, client, page, batch_size, last_sync):
        """Fetch a single page with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                if attempt == 0:
                    self.stdout.write(f"Fetching page {page}...")
                else:
                    self.stdout.write(f"Retrying page {page} (attempt {attempt + 1}/{MAX_RETRIES})")
                
                page_result = asyncio.run(client.get_tasks(
                    page_size=batch_size,
                    page=page,
                    last_sync=last_sync
                ))
                
                return page_result
                
            except Exception as e:
                error_msg = str(e)
                is_last_attempt = attempt == MAX_RETRIES - 1
                
                if is_last_attempt:
                    self.stdout.write(self.style.ERROR(
                        f"Failed to fetch page {page} after {MAX_RETRIES} attempts: {error_msg}"
                    ))
                    logger.error(f"Page {page} failed after {MAX_RETRIES} attempts: {error_msg}")
                    return None
                else:
                    delay = RETRY_DELAY * (BACKOFF_MULTIPLIER ** attempt)
                    self.stdout.write(self.style.WARNING(
                        f"Page {page} failed (attempt {attempt + 1}): {error_msg}. "
                        f"Retrying in {delay} seconds..."
                    ))
                    logger.warning(f"Page {page} attempt {attempt + 1} failed: {error_msg}")
                    time.sleep(delay)
        
        return None
