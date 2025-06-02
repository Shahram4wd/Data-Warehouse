"""
Command to sync multiple HubSpot endpoints in one operation.

For syncing specific entity types, use the dedicated commands:
- sync_hubspot_contacts: For syncing only contacts
- sync_hubspot_deals: For syncing only deals
"""
import asyncio
import logging
from datetime import datetime

import aiohttp
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.hubspot.hubspot_client import HubspotClient
from ingestion.models.hubspot import Hubspot_Contact, Hubspot_Deal, Hubspot_SyncHistory  # Updated imports

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Sync data from multiple HubSpot API endpoints (for specific entity types, use sync_hubspot_contacts or sync_hubspot_deals)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--endpoint",
            nargs="+",
            help="Specify one or more endpoints to sync. If omitted, all available endpoints will be discovered.",
        )
        parser.add_argument(
            "--concurrent",
            type=int,
            default=5,
            help="Number of endpoints to process concurrently (default: 5).",
        )
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform a full sync instead of incremental.",
        )

    def handle(self, *args, **options):
        endpoints = options.get("endpoint")
        concurrent = options.get("concurrent")
        full_sync = options.get("full")
        token = settings.HUBSPOT_API_TOKEN

        if not token:
            raise CommandError("HUBSPOT_API_TOKEN is not set in settings or environment variables.")

        self.stdout.write(self.style.SUCCESS("Starting HubSpot sync..."))
        asyncio.run(self.async_handle(endpoints, concurrent, token, full_sync))
        self.stdout.write(self.style.SUCCESS("HubSpot sync complete."))

    async def async_handle(self, endpoints, concurrent, token, full_sync):
        """Handle the async execution of the command."""
        semaphore = asyncio.Semaphore(concurrent)
        client = HubspotClient(token)
        
        async with aiohttp.ClientSession() as session:
            if not endpoints:
                endpoints = await client.discover_endpoints(session)
                self.stdout.write(self.style.SUCCESS(f"Discovered endpoints: {endpoints}"))
            
            tasks = [
                self.sync_endpoint(client, ep, session, semaphore, full_sync)
                for ep in endpoints
            ]
            await asyncio.gather(*tasks)

    async def sync_endpoint(self, client, endpoint, session, semaphore, full_sync):
        """Sync a specific endpoint from Hubspot."""
        async with semaphore:
            self.stdout.write(self.style.SUCCESS(f"Syncing endpoint: {endpoint}"))
            
            # Skip sync if full_sync is False
            last_sync = None if full_sync else await sync_to_async(self.get_last_sync)(endpoint)
            
            # Get data from Hubspot
            results = await client.get_all_data(session, endpoint, last_sync)
            
            if not results:
                self.stdout.write(self.style.WARNING(f"No data found for endpoint: {endpoint}"))
                return
                
            # Process the data
            for record in results:
                await sync_to_async(self.save_record)(endpoint, record)
                
            # Update the last sync time
            await sync_to_async(self.update_last_sync)(endpoint)
            
            self.stdout.write(self.style.SUCCESS(f"Synced {len(results)} records for endpoint: {endpoint}"))

    def get_last_sync(self, endpoint):
        """Get the last sync time for an endpoint."""
        try:
            history = Hubspot_SyncHistory.objects.get(endpoint=endpoint)
            return history.last_synced_at
        except Hubspot_SyncHistory.DoesNotExist:
            return None

    def update_last_sync(self, endpoint):
        """Update the last sync time for an endpoint."""
        history, _ = Hubspot_SyncHistory.objects.get_or_create(endpoint=endpoint)
        history.last_synced_at = timezone.now()
        history.save()

    def save_record(self, endpoint, record):
        """Save a record to the appropriate model based on the endpoint."""
        # Handle contacts
        if endpoint.lower() in ['contacts', 'contact']:
            self._save_contact(record)
        # Handle deals
        elif endpoint.lower() in ['deals', 'deal']:
            self._save_deal(record)
        # Log unhandled endpoints
        else:
            logger.warning(f"Unhandled endpoint: {endpoint}, record: {record.get('id')}")

    def _save_contact(self, record):
        """Save a contact record."""
        try:
            # Extract properties from the record
            props = record.get('properties', {})
            record_id = record.get('id')
            
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
                # Add other fields as needed
            }
            
            # Update or create the contact
            Hubspot_Contact.objects.update_or_create(  # Updated reference
                id=record_id,
                defaults=contact_data
            )
        except Exception as e:
            logger.error(f"Error saving contact {record.get('id')}: {str(e)}")

    def _save_deal(self, record):
        """Save a deal record."""
        try:
            # Extract properties from the record
            props = record.get('properties', {})
            record_id = record.get('id')
            
            # Map properties to model fields
            deal_data = {
                'id': record_id,
                'hs_object_id': props.get('hs_object_id'),
                'deal_name': props.get('dealname'),
                'amount': props.get('amount'),
                'closedate': self._parse_datetime(props.get('closedate')),
                'createdate': self._parse_datetime(props.get('createdate')),
                'dealstage': props.get('dealstage'),
                'dealtype': props.get('dealtype'),
                'description': props.get('description'),
                'hubspot_owner_id': props.get('hubspot_owner_id'),
                'pipeline': props.get('pipeline'),
                # Add other fields as needed
            }
            
            # Update or create the deal
            Hubspot_Deal.objects.update_or_create(  # Updated reference
                id=record_id,
                defaults=deal_data
            )
        except Exception as e:
            logger.error(f"Error saving deal {record.get('id')}: {str(e)}")
    
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
            logger.warning(f"Could not parse datetime: {value}")
            return None