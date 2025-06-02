import asyncio
import logging
from datetime import datetime

import aiohttp
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from tqdm import tqdm

from ingestion.hubspot.hubspot_client import HubspotClient
from ingestion.models.hubspot import HubspotDeal, HubspotSyncHistory

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Sync deals from HubSpot API"

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

    def handle(self, *args, **options):
        full_sync = options.get("full")
        limit = options.get("limit")
        token = settings.HUBSPOT_API_TOKEN

        if not token:
            raise CommandError("HUBSPOT_API_TOKEN is not set in settings or environment variables.")

        self.stdout.write(self.style.SUCCESS("Starting HubSpot deals sync..."))
        asyncio.run(self.sync_deals(token, full_sync, limit))
        self.stdout.write(self.style.SUCCESS("HubSpot deals sync complete."))

    async def sync_deals(self, token, full_sync, limit):
        """Synchronize deals from HubSpot."""
        endpoint = "deals"
        client = HubspotClient(token)
        
        # Get last sync time for incremental sync
        last_sync = None if full_sync else await sync_to_async(self.get_last_sync)(endpoint)
        if last_sync:
            self.stdout.write(f"Performing incremental sync since {last_sync}")
        else:
            self.stdout.write("Performing full sync")
        
        async with aiohttp.ClientSession() as session:
            # Get all deals from HubSpot
            deals = await client.get_all_data(session, endpoint, last_sync)
            
            if not deals:
                self.stdout.write(self.style.WARNING("No deals found to sync"))
                return
                
            # Process deals
            total_synced = await self.process_deals(deals)
            
            # Update last sync time
            await sync_to_async(self.update_last_sync)(endpoint)
            
            self.stdout.write(self.style.SUCCESS(f"Synced {total_synced} deals from HubSpot"))
    
    async def process_deals(self, deals):
        """Process and save deal records."""
        total_synced = 0
        
        for deal in tqdm(deals, desc="Syncing deals"):
            try:
                await sync_to_async(self.save_deal)(deal)
                total_synced += 1
            except Exception as e:
                logger.error(f"Error processing deal {deal.get('id')}: {str(e)}")
        
        return total_synced
    
    def get_last_sync(self, endpoint):
        """Get the last sync time for deals."""
        try:
            history = HubspotSyncHistory.objects.get(endpoint=endpoint)
            return history.last_synced_at
        except HubspotSyncHistory.DoesNotExist:
            return None

    def update_last_sync(self, endpoint):
        """Update the last sync time for deals."""
        history, _ = HubspotSyncHistory.objects.get_or_create(endpoint=endpoint)
        history.last_synced_at = timezone.now()
        history.save()
    
    def save_deal(self, record):
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
                'division': props.get('division'),
                'priority': props.get('priority'),
                # Add other fields as needed
            }
            
            # Update or create the deal
            HubspotDeal.objects.update_or_create(
                id=record_id,
                defaults=deal_data
            )
        except Exception as e:
            logger.error(f"Error saving deal {record.get('id')}: {str(e)}")
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
            logger.warning(f"Could not parse datetime: {value}")
            return None
