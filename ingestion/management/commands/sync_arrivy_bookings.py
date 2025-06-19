import asyncio
import os
import sys
import json
import logging
from datetime import datetime, timedelta

import aiohttp
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from tqdm import tqdm

from ingestion.arrivy.arrivy_client import ArrivyClient
from ingestion.models.arrivy import Arrivy_Booking, Arrivy_Customer, Arrivy_SyncHistory

logger = logging.getLogger(__name__)

BATCH_SIZE = 100

class Command(BaseCommand):
    help = "Sync bookings from Arrivy API"

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
            "--lastmodifieddate",
            type=str,
            help="Filter bookings modified after this date (YYYY-MM-DD format)"
        )
        parser.add_argument(
            "--start-date",
            type=str,
            help="Filter bookings starting after this date (YYYY-MM-DD format)"
        )
        parser.add_argument(
            "--end-date",
            type=str,
            help="Filter bookings ending before this date (YYYY-MM-DD format)"
        )

    def handle(self, *args, **options):
        full_sync = options.get("full")
        max_pages = options.get("pages", 0)
        lastmodifieddate = options.get("lastmodifieddate")
        start_date_str = options.get("start_date")
        end_date_str = options.get("end_date")

        if not all([settings.ARRIVY_API_KEY, settings.ARRIVY_AUTH_KEY, settings.ARRIVY_API_URL]):
            raise CommandError("Arrivy API credentials are not properly configured in settings.")

        self.stdout.write(self.style.SUCCESS("Starting Arrivy bookings sync..."))
        
        # Get the last sync time
        endpoint = "bookings"
        
        # Priority: 1) --lastmodifieddate parameter, 2) database last sync, 3) full sync
        if lastmodifieddate:
            try:
                last_sync = datetime.strptime(lastmodifieddate, "%Y-%m-%d")
                last_sync = timezone.make_aware(last_sync)
                self.stdout.write(f"Using provided lastmodifieddate filter: {lastmodifieddate}")
            except ValueError:
                raise CommandError(f"Invalid date format for --lastmodifieddate. Use YYYY-MM-DD format.")
        elif full_sync:
            last_sync = None
        else:
            last_sync = self.get_last_sync(endpoint)
        
        # Parse date range filters
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                start_date = timezone.make_aware(start_date)
                self.stdout.write(f"Using start date filter: {start_date_str}")
            except ValueError:
                raise CommandError(f"Invalid date format for --start-date. Use YYYY-MM-DD format.")
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                end_date = timezone.make_aware(end_date)
                self.stdout.write(f"Using end date filter: {end_date_str}")
            except ValueError:
                raise CommandError(f"Invalid date format for --end-date. Use YYYY-MM-DD format.")
        
        if last_sync:
            self.stdout.write(f"Performing delta sync since {last_sync}")
        else:
            self.stdout.write("Performing full sync")
        
        try:
            all_bookings = []
            total_pages = 0
            
            client = ArrivyClient()
            
            self.stdout.write("Starting to fetch bookings from Arrivy...")
            self.stdout.write(f"Using batch size: {BATCH_SIZE}")
            
            page = 1
            has_next = True
            
            while has_next:
                if max_pages > 0 and total_pages >= max_pages:
                    self.stdout.write(f"Reached maximum page limit of {max_pages}")
                    break

                total_pages += 1
                self.stdout.write(f"Fetching page {total_pages}...")

                page_result = asyncio.run(client.get_bookings(
                    page_size=BATCH_SIZE,
                    page=page,
                    last_sync=last_sync,
                    start_date=start_date,
                    end_date=end_date
                ))

                if not page_result or not page_result.get('data'):
                    self.stdout.write("No more data to fetch")
                    break

                page_data = page_result['data']
                pagination = page_result.get('pagination', {})
                
                self.stdout.write(f"Retrieved {len(page_data)} bookings")
                all_bookings.extend(page_data)

                has_next = pagination.get('has_next', False) if pagination else len(page_data) >= BATCH_SIZE
                page = pagination.get('next_page', page + 1) if pagination else page + 1

                # Save data if we've reached a checkpoint
                if len(all_bookings) >= BATCH_SIZE * 5:
                    self.stdout.write(f"Processing checkpoint at page {total_pages}...")
                    self.process_bookings_batch(all_bookings[:BATCH_SIZE * 5])
                    all_bookings = all_bookings[BATCH_SIZE * 5:]

            # Process any remaining bookings
            if all_bookings:
                self.stdout.write("Processing final batch...")
                self.process_bookings_batch(all_bookings)

            # Update sync history
            self.update_last_sync(endpoint)
            
            self.stdout.write(self.style.SUCCESS(f"Arrivy bookings sync complete. Processed {total_pages} pages."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in sync process: {str(e)}"))
            logger.exception("Error during Arrivy bookings sync")
            raise CommandError(f"Sync failed: {str(e)}")

    def process_bookings_batch(self, bookings_data):
        """Process a batch of bookings data."""
        if not bookings_data:
            return

        self.stdout.write(f"Processing {len(bookings_data)} bookings...")

        # Get existing bookings
        booking_ids = [booking.get('id') for booking in bookings_data if booking.get('id')]
        existing_bookings = {
            booking.id: booking 
            for booking in Arrivy_Booking.objects.filter(id__in=booking_ids)
        }

        # Get existing customers for foreign key relationships
        customer_ids = [booking.get('customer_id') for booking in bookings_data if booking.get('customer_id')]
        existing_customers = {
            customer.id: customer 
            for customer in Arrivy_Customer.objects.filter(id__in=customer_ids)
        }

        bookings_to_create = []
        bookings_to_update = []

        for booking_data in bookings_data:
            try:
                booking_id = booking_data.get('id')
                if not booking_id:
                    continue

                # Parse datetime fields
                start_datetime = self.parse_datetime(booking_data.get('start_datetime'))
                end_datetime = self.parse_datetime(booking_data.get('end_datetime'))
                actual_start_datetime = self.parse_datetime(booking_data.get('actual_start_datetime'))
                actual_end_datetime = self.parse_datetime(booking_data.get('actual_end_datetime'))
                created_time = self.parse_datetime(booking_data.get('created_time'))
                updated_time = self.parse_datetime(booking_data.get('updated_time'))

                # Get customer relationship
                customer_id = booking_data.get('customer_id')
                customer = existing_customers.get(customer_id) if customer_id else None

                # Handle team member assignments
                assigned_team_members = booking_data.get('assigned_team_members', [])
                team_member_ids = ",".join([str(tm_id) for tm_id in assigned_team_members if tm_id])

                # Prepare booking fields
                booking_fields = {
                    'external_id': booking_data.get('external_id'),
                    'customer_id': customer_id,
                    'customer': customer,
                    'title': booking_data.get('title'),
                    'description': booking_data.get('description'),
                    'details': booking_data.get('details'),
                    'start_datetime': start_datetime,
                    'end_datetime': end_datetime,
                    'start_datetime_original_iso_str': booking_data.get('start_datetime_original_iso_str'),
                    'end_datetime_original_iso_str': booking_data.get('end_datetime_original_iso_str'),
                    'timezone': booking_data.get('timezone'),
                    'status': booking_data.get('status'),
                    'status_id': booking_data.get('status_id'),
                    'task_type': booking_data.get('task_type'),
                    'address_line_1': booking_data.get('address_line_1'),
                    'address_line_2': booking_data.get('address_line_2'),
                    'city': booking_data.get('city'),
                    'state': booking_data.get('state'),
                    'country': booking_data.get('country'),
                    'zipcode': booking_data.get('zipcode'),
                    'exact_location': booking_data.get('exact_location'),
                    'assigned_team_members': assigned_team_members,
                    'team_member_ids': team_member_ids,
                    'template_id': booking_data.get('template_id'),
                    'template_extra_fields': booking_data.get('template_extra_fields'),
                    'extra_fields': booking_data.get('extra_fields'),
                    'custom_fields': booking_data.get('custom_fields'),
                    'actual_start_datetime': actual_start_datetime,
                    'actual_end_datetime': actual_end_datetime,
                    'duration_estimate': booking_data.get('duration_estimate'),
                    'is_recurring': booking_data.get('is_recurring', False),
                    'is_all_day': booking_data.get('is_all_day', False),
                    'enable_time_window_display': booking_data.get('enable_time_window_display', False),
                    'unscheduled': booking_data.get('unscheduled', False),
                    'notifications': booking_data.get('notifications'),
                    'created_time': created_time,
                    'updated_time': updated_time,
                }

                if booking_id in existing_bookings:
                    # Update existing booking
                    booking = existing_bookings[booking_id]
                    for field, value in booking_fields.items():
                        setattr(booking, field, value)
                    bookings_to_update.append(booking)
                else:
                    # Create new booking
                    booking_fields['id'] = booking_id
                    bookings_to_create.append(Arrivy_Booking(**booking_fields))

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error processing booking {booking_data.get('id', 'unknown')}: {str(e)}"))
                continue

        # Bulk save to database
        created, updated = self.save_bookings(bookings_to_create, bookings_to_update)
        self.stdout.write(f"Created {created} bookings, updated {updated} bookings")

    def save_bookings(self, bookings_to_create, bookings_to_update):
        """Save bookings to database with error handling."""
        created_count = 0
        updated_count = 0

        try:
            with transaction.atomic():
                if bookings_to_create:
                    Arrivy_Booking.objects.bulk_create(bookings_to_create, batch_size=BATCH_SIZE, ignore_conflicts=True)
                    created_count = len(bookings_to_create)

                if bookings_to_update:
                    update_fields = [
                        'external_id', 'customer_id', 'customer', 'title', 'description', 'details',
                        'start_datetime', 'end_datetime', 'start_datetime_original_iso_str',
                        'end_datetime_original_iso_str', 'timezone', 'status', 'status_id', 'task_type',
                        'address_line_1', 'address_line_2', 'city', 'state', 'country', 'zipcode',
                        'exact_location', 'assigned_team_members', 'team_member_ids', 'template_id',
                        'template_extra_fields', 'extra_fields', 'custom_fields', 'actual_start_datetime',
                        'actual_end_datetime', 'duration_estimate', 'is_recurring', 'is_all_day',
                        'enable_time_window_display', 'unscheduled', 'notifications', 'created_time', 'updated_time'
                    ]
                    
                    Arrivy_Booking.objects.bulk_update(bookings_to_update, update_fields, batch_size=BATCH_SIZE)
                    updated_count = len(bookings_to_update)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error saving bookings: {str(e)}"))
            logger.exception("Error saving bookings to database")
            raise

        return created_count, updated_count

    def get_last_sync(self, endpoint):
        """Get the last sync time for bookings."""
        try:
            history = Arrivy_SyncHistory.objects.get(endpoint=endpoint)
            return history.last_synced_at
        except Arrivy_SyncHistory.DoesNotExist:
            return None

    def update_last_sync(self, endpoint):
        """Update the last sync time for bookings."""
        history, created = Arrivy_SyncHistory.objects.get_or_create(
            endpoint=endpoint,
            defaults={'last_synced_at': timezone.now()}
        )
        history.last_synced_at = timezone.now()
        history.save()

    def parse_datetime(self, value):
        """Parse a datetime string into a datetime object."""
        if not value:
            return None
        
        try:
            for fmt in [
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
            ]:
                try:
                    dt = datetime.strptime(value, fmt)
                    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
                except ValueError:
                    continue
            
            logger.warning(f"Could not parse datetime: {value}")
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing datetime {value}: {str(e)}")
            return None
