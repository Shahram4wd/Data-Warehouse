import asyncio
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import List, Tuple

import aiohttp
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from tqdm import tqdm

from ingestion.hubspot.hubspot_client import HubspotClient
from ingestion.models.hubspot import Hubspot_Contact, Hubspot_SyncHistory

logger = logging.getLogger(__name__)

BATCH_SIZE = 100  # Adjust batch size to process more contacts per checkpoint

class Command(BaseCommand):
    help = "Sync contacts from HubSpot API"

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
        parser.add_argument(            "--lastmodifieddate",
            type=str,
            help="Filter contacts modified after this date (YYYY-MM-DD format)"
        )

    def handle(self, *args, **options):
        full_sync = options.get("full")
        max_pages = options.get("pages", 0)
        checkpoint_interval = options.get("checkpoint", 5)
        lastmodifieddate = options.get("lastmodifieddate")
        token = settings.HUBSPOT_API_TOKEN

        if not token:
            raise CommandError("HUBSPOT_API_TOKEN is not set in settings or environment variables.")

        self.stdout.write(self.style.SUCCESS("Starting HubSpot contacts sync..."))
        
        # Run the async sync
        try:
            asyncio.run(self.sync_contacts(options, token))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Sync failed: {str(e)}'))
            logger.error(f"HubSpot contacts sync failed: {str(e)}")

    async def sync_contacts(self, options, token):
        """Main sync logic"""
        full_sync = options.get("full")
        lastmodifieddate = options.get("lastmodifieddate")
        
        # Get the last sync time
        endpoint = "contacts"
        
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
            last_sync = await self.get_last_sync_async(endpoint)
        
        if last_sync:
            self.stdout.write(f"Performing delta sync since {last_sync}")
        else:
            self.stdout.write("Performing full sync")
        
        # Initialize client
        client = HubspotClient(token)
        
        # Process in a completely separated way - fetch data using adaptive chunking, then process it
        try:
            # Use adaptive chunking similar to appointments sync
            all_contacts = await self._fetch_contacts_adaptive(client, last_sync, timezone.now())
            
            # Process all fetched contacts
            if all_contacts:
                self.stdout.write(f"Processing {len(all_contacts)} total contacts...")
                total_created, total_updated = await self._process_contacts_async(all_contacts)
                self.stdout.write(self.style.SUCCESS(f"Created {total_created} contacts, updated {total_updated} contacts"))

            # Update last sync time
            await self._update_last_sync_async(endpoint)

            self.stdout.write(self.style.SUCCESS(f"HubSpot contacts sync complete. Processed {len(all_contacts)} contacts."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in sync process: {str(e)}"))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))

    def process_contacts_batch(self, contacts):
        """Process a batch of contacts and save them to the database."""
        if not contacts:
            return 0, 0
            
        created = 0
        updated = 0
        
        self.stdout.write(f"Processing {len(contacts)} contacts...")
        
        # Collect existing contact IDs
        contact_ids = [contact.get('id') for contact in contacts if contact.get('id')]
        existing_contacts = Hubspot_Contact.objects.in_bulk(contact_ids)
        
        to_create = []
        to_update = []
        
        # Process each contact with progress bar
        for contact in tqdm(contacts, desc="Processing contacts"):
            try:
                # Get basic info
                record_id = contact.get('id')
                if not record_id:
                    continue
                
                # Extract properties
                props = contact.get('properties', {})
                
                # Prepare contact data
                contact_data = {
                    'firstname': props.get('firstname'),
                    'lastname': props.get('lastname'),
                    'email': props.get('email'),
                    'phone': props.get('phone'),
                    'address': props.get('address'),
                    'city': props.get('city'),
                    'state': props.get('state'),
                    'zip': props.get('zip'),
                    'hs_object_id': props.get('hs_object_id'),
                    'createdate': self._parse_datetime(props.get('createdate')),
                    'lastmodifieddate': self._parse_datetime(props.get('lastmodifieddate')),
                    'campaign_name': props.get('campaign_name'),
                    'division': props.get('division'),
                    'marketsharp_id': props.get('marketsharp_id'),
                    'hs_google_click_id': props.get('hs_google_click_id'),
                    'original_lead_source': props.get('original_lead_source'),
                    'original_lead_source_created': self._parse_datetime(props.get('original_lead_source_created')),
                    'adgroupid': props.get('adgroupid'),
                    'ap_leadid': props.get('ap_leadid'),
                    'campaign_content': props.get('campaign_content'),
                    'clickcheck': props.get('clickcheck'),
                    'clicktype': props.get('clicktype'),
                    'comments': props.get('comments'),
                    'lead_salesrabbit_lead_id': props.get('lead_salesrabbit_lead_id'),
                    'msm_source': props.get('msm_source'),
                    'price': props.get('price'),
                    'reference_code': props.get('reference_code'),
                    'search_terms': props.get('search_terms'),
                    'tier': props.get('tier'),
                    'trustedform_cert_url': props.get('trustedform_cert_url'),
                    'vendorleadid': props.get('vendorleadid'),
                    'vertical': props.get('vertical'),
                }
                
                if record_id in existing_contacts:
                    # Update existing contact
                    contact_obj = existing_contacts[record_id]
                    for key, value in contact_data.items():
                        setattr(contact_obj, key, value)
                    to_update.append(contact_obj)
                else:
                    # Create new contact
                    to_create.append(Hubspot_Contact(id=record_id, **contact_data))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing contact {contact.get('id')}: {str(e)}"))
        
        # Save to database with transaction
        try:
            with transaction.atomic():
                if to_create:
                    Hubspot_Contact.objects.bulk_create(to_create)
                    created = len(to_create)
                    self.stdout.write(self.style.SUCCESS(f"Created {created} contacts"))
                
                if to_update:
                    # Exclude primary key and auto fields
                    update_fields = [f.name for f in Hubspot_Contact._meta.fields 
                                   if not f.primary_key and not f.auto_created]
                    
                    Hubspot_Contact.objects.bulk_update(to_update, update_fields)
                    updated = len(to_update)
                    self.stdout.write(self.style.SUCCESS(f"Updated {updated} contacts"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error saving contacts: {str(e)}"))
            # Fall back to individual saves
            for obj in to_create:
                try:
                    obj.save()
                    created += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error saving contact {obj.id}: {str(e)}"))
            
            for obj in to_update:
                try:
                    obj.save()
                    updated += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error updating contact {obj.id}: {str(e)}"))
        
        return created, updated
    
    def get_last_sync(self, endpoint):
        """Get the last sync time for contacts."""
        try:
            history = Hubspot_SyncHistory.objects.get(endpoint=endpoint)
            return history.last_synced_at
        except Hubspot_SyncHistory.DoesNotExist:
            return None

    def update_last_sync(self, endpoint):
        """Update the last sync time for contacts."""
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
                timestamp = int(value) / 1000  # Convert from milliseconds to seconds
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            
            # Try parsing as ISO format
            if isinstance(value, str):
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
                
            return value
        except (ValueError, TypeError):
            logger.warning(f"Could not parse datetime: {value}")
            return None

    async def _fetch_contacts_adaptive(self, client, start_date, end_date, max_results_per_chunk=8000):
        """
        Adaptively fetch contacts by breaking down time ranges when errors occur or too many results are returned.
        
        Args:
            client: HubspotClient instance
            start_date: Start datetime for the range (None for full sync)
            end_date: End datetime for the range
            max_results_per_chunk: Maximum number of results per chunk before subdividing
        
        Returns:
            List of all contacts fetched
        """
        all_contacts = []
        
        # If no start_date, do a full fetch without date range
        if start_date is None:
            self.stdout.write("Performing full contact fetch without date filtering...")
            return await self._fetch_all_contacts_paginated(client)
        
        # Create initial time ranges to process
        pending_ranges = [(start_date, end_date)]
        
        while pending_ranges:
            current_start, current_end = pending_ranges.pop(0)
            time_span = current_end - current_start
            
            self.stdout.write(f"Processing range: {current_start} to {current_end} (span: {time_span})")
            
            try:
                # Try to fetch this chunk
                chunk_contacts = await self._fetch_single_chunk(client, current_start, current_end)
                
                if len(chunk_contacts) > max_results_per_chunk:
                    # Too many results, subdivide the time range
                    self.stdout.write(f"⚠️ Chunk too large ({len(chunk_contacts)} contacts), subdividing...")
                    subdivisions = self._subdivide_time_range(current_start, current_end, 4)
                    pending_ranges.extend(subdivisions)
                else:
                    # Acceptable chunk size
                    all_contacts.extend(chunk_contacts)
                    self.stdout.write(f"✅ Processed range: {len(chunk_contacts)} contacts")
            
            except Exception as e:
                error_msg = str(e)
                self.stdout.write(f"❌ Error fetching range {current_start} to {current_end}: {error_msg}")
                
                # If it's a large time span, try subdividing
                if time_span.days > 1:
                    self.stdout.write("Subdividing range due to error...")
                    subdivisions = self._subdivide_time_range(current_start, current_end, 7)
                    pending_ranges.extend(subdivisions)
                else:
                    # Small range still failing, skip it but log the error
                    self.stdout.write(f"⚠️ Skipping problematic range: {current_start} to {current_end}")
                    logger.error(f"Failed to fetch contacts for range {current_start} to {current_end}: {error_msg}")
        
        self.stdout.write(f"✅ Adaptive fetch complete: {len(all_contacts)} total contacts")
        return all_contacts
    
    async def _fetch_all_contacts_paginated(self, client):
        """Fetch all contacts using standard pagination for full sync."""
        all_contacts = []
        next_page_token = None
        page_num = 0
        
        while True:
            page_num += 1
            self.stdout.write(f"Fetching page {page_num}...")
            
            try:
                page_result = await client.get_page(
                    endpoint="contacts",
                    last_sync=None,
                    page_token=next_page_token
                )
                
                if not page_result or not page_result[0]:
                    self.stdout.write("No more data to fetch")
                    break
                
                page_data, next_page_token = page_result
                self.stdout.write(f"Retrieved {len(page_data)} contacts")
                all_contacts.extend(page_data)
                
                if not next_page_token:
                    self.stdout.write("No more pages available")
                    break
                    
            except Exception as e:
                self.stdout.write(f"Error fetching page {page_num}: {str(e)}")
                break
        
        return all_contacts
    
    async def _fetch_single_chunk(self, client, start_date, end_date):
        """
        Fetch a single chunk of contacts for the given date range.
        
        Args:
            client: HubspotClient instance
            start_date: Start datetime
            end_date: End datetime
            
        Returns:
            List of contacts for this range
        """
        all_contacts = []
        next_page_token = None
        page_num = 0
        
        while True:
            page_num += 1
            
            try:
                page_result = await client.get_page(
                    endpoint="contacts",
                    last_sync=start_date,
                    page_token=next_page_token
                )
                
                if not page_result or not page_result[0]:
                    break
                
                page_data, next_page_token = page_result
                
                # Filter by end_date if necessary
                filtered_contacts = []
                for contact in page_data:
                    contact_modified = self._parse_datetime(contact.get('properties', {}).get('lastmodifieddate'))
                    if contact_modified and contact_modified <= end_date:
                        filtered_contacts.append(contact)
                    elif not contact_modified:
                        # Include contacts without lastmodifieddate
                        filtered_contacts.append(contact)
                
                all_contacts.extend(filtered_contacts)
                
                if not next_page_token:
                    break
                    
            except Exception as e:
                raise e
        
        return all_contacts
    
    def _subdivide_time_range(self, start_date, end_date, num_subdivisions=4):
        """
        Subdivide a time range into smaller equal chunks.
        
        Args:
            start_date: Start datetime
            end_date: End datetime
            num_subdivisions: Number of equal subdivisions to create
            
        Returns:
            List of (start, end) tuples for each subdivision
        """
        total_seconds = (end_date - start_date).total_seconds()
        chunk_seconds = total_seconds / num_subdivisions
        
        subdivisions = []
        current_start = start_date
        
        for i in range(num_subdivisions):
            if i == num_subdivisions - 1:
                # Last chunk goes to the end
                subdivisions.append((current_start, end_date))
            else:
                current_end = current_start + timedelta(seconds=chunk_seconds)
                subdivisions.append((current_start, current_end))
                current_start = current_end
        
        self.stdout.write(f"📋 Created {len(subdivisions)} subdivisions of {timedelta(seconds=chunk_seconds)} each")
        return subdivisions

    @sync_to_async
    def _process_contacts_async(self, contacts):
        """Process contacts asynchronously"""
        return self.process_contacts_batch(contacts)

    @sync_to_async
    def _update_last_sync_async(self, endpoint):
        """Update the last sync time asynchronously"""
        self.update_last_sync(endpoint)

    @sync_to_async
    def get_last_sync_async(self, endpoint):
        """Get the last sync time for contacts asynchronously."""
        return self.get_last_sync(endpoint)
