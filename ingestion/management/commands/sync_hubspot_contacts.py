import asyncio
import logging
import sys
import json
import time
from datetime import datetime

import aiohttp
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.hubspot.hubspot_client import HubspotClient
from ingestion.models.hubspot import Hubspot_Contact, Hubspot_SyncHistory  # Updated imports

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Sync contacts from HubSpot API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform a full sync instead of incremental."
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Number of records to fetch per request (max 100)"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable extra debug output"
        )

    def handle(self, *args, **options):
        full_sync = options.get("full")
        limit = options.get("limit")
        debug = options.get("debug", False)
        token = settings.HUBSPOT_API_TOKEN

        if not token:
            raise CommandError("HUBSPOT_API_TOKEN is not set in settings or environment variables.")

        self.stdout.write(self.style.SUCCESS("Starting HubSpot contacts sync..."))
        self.stdout.write(f"Using API token: {token[:5]}...{token[-5:]} (length: {len(token)})")
        
        if debug:
            # Set up more verbose logging for debugging
            root = logging.getLogger()
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            root.addHandler(handler)
            root.setLevel(logging.DEBUG)
            
        try:
            # Run with a timeout to prevent hanging
            result = asyncio.run(self.sync_contacts_with_timeout(token, full_sync, limit, timeout=120))
            if result:
                self.stdout.write(self.style.SUCCESS("HubSpot contacts sync complete."))
            else:
                self.stdout.write(self.style.ERROR("HubSpot contacts sync timed out."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in sync_contacts: {str(e)}"))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))

    async def sync_contacts_with_timeout(self, token, full_sync, limit, timeout=120):
        """Run the sync with a timeout to prevent hanging."""
        try:
            # Create a task for the sync
            sync_task = asyncio.create_task(self.sync_contacts(token, full_sync, limit))
            
            # Wait for the task to complete with a timeout
            done, pending = await asyncio.wait([sync_task], timeout=timeout)
            
            if sync_task in pending:
                # Task didn't complete within the timeout
                sync_task.cancel()
                self.stdout.write(self.style.ERROR(f"Sync operation timed out after {timeout} seconds."))
                return False
                
            # Task completed, check the result
            return sync_task.result()
            
        except asyncio.CancelledError:
            self.stdout.write(self.style.ERROR("Sync operation was cancelled."))
            return False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in sync_contacts_with_timeout: {str(e)}"))
            return False

    async def sync_contacts(self, token, full_sync, limit):
        """Synchronize contacts from HubSpot."""
        endpoint = "contacts"
        client = HubspotClient(token)
        
        # Get last sync time for incremental sync
        last_sync = None if full_sync else await sync_to_async(self.get_last_sync)(endpoint)
        if last_sync:
            self.stdout.write(f"Performing incremental sync since {last_sync}")
        else:
            self.stdout.write("Performing full sync")
        
        try:
            async with aiohttp.ClientSession() as session:
                self.stdout.write("Starting API request to HubSpot...")
                
                # Add a timeout for the API request
                start_time = time.time()
                try:
                    # Get all contacts from HubSpot with a timeout
                    contacts = await asyncio.wait_for(
                        client.get_all_data(session, endpoint, last_sync),
                        timeout=60  # 60 second timeout for the entire request
                    )
                except asyncio.TimeoutError:
                    self.stdout.write(self.style.ERROR("API request timed out after 60 seconds"))
                    return False
                
                elapsed_time = time.time() - start_time
                self.stdout.write(f"API request completed in {elapsed_time:.2f} seconds")
                
                if not contacts:
                    self.stdout.write(self.style.WARNING("No contacts found to sync. API returned empty results."))
                    return True
                
                self.stdout.write(f"Retrieved {len(contacts)} contacts from HubSpot")
                
                # Process a limited number of contacts for testing
                test_limit = min(len(contacts), 5)
                self.stdout.write(f"Processing {test_limit} contacts for testing")
                
                total_synced = 0
                for i, contact in enumerate(contacts[:test_limit]):
                    self.stdout.write(f"Processing contact {i+1}/{test_limit}")
                    
                    try:
                        # Print sample of contact data
                        contact_preview = json.dumps(contact)[:200] + "..."
                        self.stdout.write(f"Contact data preview: {contact_preview}")
                        
                        await sync_to_async(self.save_contact)(contact)
                        total_synced += 1
                        self.stdout.write(f"Successfully saved contact {i+1}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error processing contact {i+1}: {str(e)}"))
                
                # Update last sync time
                if total_synced > 0:
                    await sync_to_async(self.update_last_sync)(endpoint)
                
                self.stdout.write(self.style.SUCCESS(f"Synced {total_synced} contacts from HubSpot"))
                return True
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in API request or processing: {str(e)}"))
            return False
    
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
    
    def save_contact(self, record):
        """Save a contact record."""
        try:
            # Extract properties from the record
            props = record.get('properties', {})
            record_id = record.get('id')
            
            if not record_id:
                print(f"Missing ID in record: {record}")
                return
                
            print(f"Saving contact {record_id}: {props.get('firstname')} {props.get('lastname')}")
            
            # Map properties to model fields
            contact_data = {
                'id': record_id,
                'hs_object_id': props.get('hs_object_id'),
                'firstname': props.get('firstname'),
                'lastname': props.get('lastname'),
                'email': props.get('email'),
                'phone': props.get('phone'),
                'address': props.get('address'),
                'city': props.get('city'),
                'state': props.get('state'),
                'zip': props.get('zip'),
                'createdate': self._parse_datetime(props.get('createdate')),
                'lastmodifieddate': self._parse_datetime(props.get('lastmodifieddate')),
                'campaign_name': props.get('campaign_name'),
                'hs_google_click_id': props.get('hs_google_click_id'),
                'original_lead_source': props.get('original_lead_source'),
                'division': props.get('division'),
                'marketsharp_id': props.get('marketsharp_id'),
            }
            
            # Print the data being saved
            print(f"Contact data to save: {json.dumps(contact_data, default=str)[:500]}...")
            
            # Update or create the contact
            Hubspot_Contact.objects.update_or_create(  # Updated reference
                id=record_id,
                defaults=contact_data
            )
        except Exception as e:
            print(f"Error saving contact {record.get('id')}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise
    
    def _parse_datetime(self, value):
        """Parse a datetime string into a datetime object."""
        if not value:
            return None
            
        try:
            # HubSpot often uses milliseconds since epoch
            if value.isdigit():
                timestamp = int(value) / 1000  # Convert from milliseconds to seconds
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            
            # Try parsing as ISO format
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            print(f"Could not parse datetime: {value}")
            return None
