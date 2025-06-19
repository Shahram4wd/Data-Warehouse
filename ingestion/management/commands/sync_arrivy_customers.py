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
from ingestion.models.arrivy import Arrivy_Customer, Arrivy_SyncHistory

logger = logging.getLogger(__name__)

BATCH_SIZE = 100  # Adjust batch size to process more customers per checkpoint

class Command(BaseCommand):
    help = "Sync customers from Arrivy API"

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
            help="Filter customers modified after this date (YYYY-MM-DD format)"
        )

    def handle(self, *args, **options):
        full_sync = options.get("full")
        max_pages = options.get("pages", 0)
        lastmodifieddate = options.get("lastmodifieddate")

        if not all([settings.ARRIVY_API_KEY, settings.ARRIVY_AUTH_KEY, settings.ARRIVY_API_URL]):
            raise CommandError("Arrivy API credentials are not properly configured in settings.")

        self.stdout.write(self.style.SUCCESS("Starting Arrivy customers sync..."))
        
        # Get the last sync time
        endpoint = "customers"
        
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
        
        # Process in a completely separated way - fetch data, then process it
        try:
            # Step 1: Fetch all pages of data asynchronously
            all_customers = []
            total_pages = 0
            
            # Start async event loop
            client = ArrivyClient()
            
            self.stdout.write("Starting to fetch customers from Arrivy...")
            self.stdout.write(f"Using batch size: {BATCH_SIZE}")
            
            page = 1
            has_next = True
            
            while has_next:
                # Check if we've reached the maximum number of pages
                if max_pages > 0 and total_pages >= max_pages:
                    self.stdout.write(f"Reached maximum page limit of {max_pages}")
                    break

                # Fetch a single page
                total_pages += 1
                self.stdout.write(f"Fetching page {total_pages}...")

                page_result = asyncio.run(client.get_customers(
                    page_size=BATCH_SIZE,
                    page=page,
                    last_sync=last_sync
                ))

                if not page_result or not page_result.get('data'):
                    self.stdout.write("No more data to fetch")
                    break

                page_data = page_result['data']
                pagination = page_result.get('pagination') or {}
                
                self.stdout.write(f"Retrieved {len(page_data)} customers")
                all_customers.extend(page_data)

                # Check if there are more pages
                has_next = pagination.get('has_next', False)
                  # If no pagination info, check if we got a full page
                if not pagination:
                    has_next = len(page_data) >= BATCH_SIZE
                
                page = pagination.get('next_page', page + 1)

                # Save data if we've reached a checkpoint
                if len(all_customers) >= BATCH_SIZE * 5:  # Process every 5 pages
                    self.stdout.write(f"Processing checkpoint at page {total_pages}...")
                    self.process_customers_batch(all_customers[:BATCH_SIZE * 5])
                    all_customers = all_customers[BATCH_SIZE * 5:]  # Keep remaining customers

            # Process any remaining customers
            if all_customers:
                self.stdout.write("Processing final batch...")
                self.process_customers_batch(all_customers)

            # Update sync history
            self.update_last_sync(endpoint)
            
            self.stdout.write(self.style.SUCCESS(f"Arrivy customers sync complete. Processed {total_pages} pages."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in sync process: {str(e)}"))
            logger.exception("Error during Arrivy customers sync")
            raise CommandError(f"Sync failed: {str(e)}")

    def process_customers_batch(self, customers_data):
        """Process a batch of customers data."""
        if not customers_data:
            return

        self.stdout.write(f"Processing {len(customers_data)} customers...")

        # Get existing customers
        customer_ids = [customer.get('id') for customer in customers_data if customer.get('id')]
        existing_customers = {
            customer.id: customer 
            for customer in Arrivy_Customer.objects.filter(id__in=customer_ids)
        }

        customers_to_create = []
        customers_to_update = []

        for customer_data in customers_data:
            try:
                customer_id = customer_data.get('id')
                if not customer_id:
                    continue

                # Parse datetime fields
                created_time = self.parse_datetime(customer_data.get('created_time'))
                updated_time = self.parse_datetime(customer_data.get('updated_time'))

                # Prepare customer fields
                customer_fields = {
                    'external_id': customer_data.get('external_id'),
                    'company_name': customer_data.get('company_name'),
                    'first_name': customer_data.get('first_name'),
                    'last_name': customer_data.get('last_name'),
                    'email': customer_data.get('email'),
                    'phone': customer_data.get('phone'),
                    'mobile_number': customer_data.get('mobile_number'),
                    'address_line_1': customer_data.get('address_line_1'),
                    'address_line_2': customer_data.get('address_line_2'),
                    'city': customer_data.get('city'),
                    'state': customer_data.get('state'),
                    'country': customer_data.get('country'),
                    'zipcode': customer_data.get('zipcode'),
                    'timezone': customer_data.get('timezone'),
                    'notes': customer_data.get('notes'),
                    'extra_fields': customer_data.get('extra_fields'),
                    'is_active': customer_data.get('is_active', True),
                    'created_time': created_time,
                    'updated_time': updated_time,
                }

                if customer_id in existing_customers:
                    # Update existing customer
                    customer = existing_customers[customer_id]
                    for field, value in customer_fields.items():
                        setattr(customer, field, value)
                    customers_to_update.append(customer)
                else:
                    # Create new customer
                    customer_fields['id'] = customer_id
                    customers_to_create.append(Arrivy_Customer(**customer_fields))

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error processing customer {customer_data.get('id', 'unknown')}: {str(e)}"))
                continue

        # Bulk save to database
        created, updated = self.save_customers(customers_to_create, customers_to_update)
        self.stdout.write(f"Created {created} customers, updated {updated} customers")

    def save_customers(self, customers_to_create, customers_to_update):
        """Save customers to database with error handling."""
        created_count = 0
        updated_count = 0

        try:
            with transaction.atomic():
                if customers_to_create:
                    created_before = Arrivy_Customer.objects.count()
                    Arrivy_Customer.objects.bulk_create(
                        customers_to_create, 
                        batch_size=BATCH_SIZE,
                        ignore_conflicts=True
                    )
                    created_after = Arrivy_Customer.objects.count()
                    created_count = created_after - created_before

                if customers_to_update:
                    # Get the fields to update (exclude id and tracking fields)
                    update_fields = [
                        'external_id', 'company_name', 'first_name', 'last_name', 'email', 'phone',
                        'mobile_number', 'address_line_1', 'address_line_2', 'city', 'state', 'country',
                        'zipcode', 'timezone', 'notes', 'extra_fields', 'is_active', 'created_time', 'updated_time'
                    ]
                    
                    Arrivy_Customer.objects.bulk_update(customers_to_update, update_fields, batch_size=BATCH_SIZE)
                    updated_count = len(customers_to_update)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error saving customers: {str(e)}"))
            logger.exception("Error saving customers to database")
            raise

        return created_count, updated_count

    def get_last_sync(self, endpoint):
        """Get the last sync time for customers."""
        try:
            history = Arrivy_SyncHistory.objects.get(endpoint=endpoint)
            return history.last_synced_at
        except Arrivy_SyncHistory.DoesNotExist:
            return None

    def update_last_sync(self, endpoint):
        """Update the last sync time for customers."""
        now = timezone.now()
        history, created = Arrivy_SyncHistory.objects.get_or_create(
            endpoint=endpoint,
            defaults={'last_synced_at': now}
        )
        if not created:
            history.last_synced_at = now
            history.save()

    def parse_datetime(self, value):
        """Parse a datetime string into a datetime object."""
        if not value:
            return None
        
        try:
            # Try different datetime formats that Arrivy might use
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
            
            # If none of the formats work, log and return None
            logger.warning(f"Could not parse datetime: {value}")
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing datetime {value}: {str(e)}")
            return None
