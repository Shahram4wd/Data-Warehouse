import asyncio
import os
import sys
import json
import logging
from datetime import datetime

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

BATCH_SIZE = 100  # Process 100 records at a time

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

    def handle(self, *args, **options):
        full_sync = options.get("full")
        max_pages = options.get("pages", 0)
        checkpoint_interval = options.get("checkpoint", 5)
        token = settings.HUBSPOT_API_TOKEN

        if not token:
            raise CommandError("HUBSPOT_API_TOKEN is not set in settings or environment variables.")

        self.stdout.write(self.style.SUCCESS("Starting HubSpot contacts sync..."))
        
        # Get the last sync time
        endpoint = "contacts"
        last_sync = None if full_sync else self.get_last_sync(endpoint)
        
        if last_sync:
            self.stdout.write(f"Performing delta sync since {last_sync}")
        else:
            self.stdout.write("Performing full sync")
        
        # Process in a completely separated way - fetch data, then process it
        try:
            # Step 1: Fetch all pages of data asynchronously
            all_contacts = []
            total_pages = 0
            
            # Start async event loop
            next_page_token = None
            client = HubspotClient(token)
            
            self.stdout.write("Starting to fetch contacts from HubSpot...")
            
            while True:
                # Check if we've reached the maximum number of pages
                if max_pages > 0 and total_pages >= max_pages:
                    self.stdout.write(f"Reached maximum page limit of {max_pages}")
                    break
                
                # Fetch a single page
                total_pages += 1
                self.stdout.write(f"Fetching page {total_pages}...")
                
                # Use asyncio.run for each page to reset the async context
                page_result = asyncio.run(client.get_page(
                    endpoint=endpoint,
                    last_sync=last_sync,
                    page_token=next_page_token
                ))
                
                if not page_result or not page_result[0]:
                    self.stdout.write("No more data to fetch")
                    break
                
                page_data, next_page_token = page_result
                self.stdout.write(f"Retrieved {len(page_data)} contacts")
                all_contacts.extend(page_data)
                
                # Save data if we've reached a checkpoint
                if total_pages % checkpoint_interval == 0:
                    self.stdout.write(f"Processing checkpoint at page {total_pages}...")
                    self.process_contacts_batch(all_contacts)
                    # Clear the contacts list to free memory
                    all_contacts = []
                
                # If no next page token, we're done
                if not next_page_token:
                    self.stdout.write("No more pages available")
                    break
            
            # Process any remaining contacts
            if all_contacts:
                self.stdout.write(f"Processing final batch of {len(all_contacts)} contacts...")
                self.process_contacts_batch(all_contacts)
            
            # Update last sync time
            self.update_last_sync(endpoint)
            
            self.stdout.write(self.style.SUCCESS(f"HubSpot contacts sync complete. Processed {total_pages} pages."))
            
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
