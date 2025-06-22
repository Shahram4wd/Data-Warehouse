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
from ingestion.models.hubspot import Hubspot_Deal, Hubspot_SyncHistory

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
        
        # Fetch all deals page by page
        all_deals = []
        total_pages = 0
        next_page_token = None
        
        self.stdout.write("Starting to fetch deals from HubSpot...")
        
        while True:
            total_pages += 1
            self.stdout.write(f"Fetching page {total_pages}...")
            
            page_result = await client.get_page(
                endpoint=endpoint,
                last_sync=last_sync,
                page_token=next_page_token,
                limit=limit
            )
            
            if not page_result or not page_result[0]:
                self.stdout.write("No more data to fetch")
                break
                
            page_data, next_page_token = page_result
            self.stdout.write(f"Retrieved {len(page_data)} deals")
            all_deals.extend(page_data)
            
            # If no next page token, we're done
            if not next_page_token:
                self.stdout.write("No more pages available")
                break
        
        if not all_deals:
            self.stdout.write(self.style.WARNING("No deals found to sync"))
            return
            
        # Process deals
        total_synced = await self.process_deals(all_deals)
        
        # Update last sync time
        await sync_to_async(self.update_last_sync)(endpoint)
        
        self.stdout.write(self.style.SUCCESS(f"Synced {total_synced} deals from HubSpot. Processed {total_pages} pages."))
    
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
            history = Hubspot_SyncHistory.objects.get(endpoint=endpoint)
            return history.last_synced_at
        except Hubspot_SyncHistory.DoesNotExist:
            return None    def update_last_sync(self, endpoint):
        """Update the last sync time for deals."""
        history, _ = Hubspot_SyncHistory.objects.get_or_create(endpoint=endpoint)
        history.last_synced_at = timezone.now()
        history.save()
    
    def save_deal(self, record):
        """Save a deal record with delta field-level updates."""
        try:
            # Extract properties from the record
            props = record.get('properties', {})
            record_id = record.get('id')
            
            # Map properties to model fields
            new_data = {
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
            
            # Get existing record or create new one
            deal, created = Hubspot_Deal.objects.get_or_create(
                id=record_id,
                defaults=new_data
            )
            
            if created:
                logger.info(f"Created new deal: {record_id}")
                return True
            
            # For existing records, only update changed fields
            changed_fields = []
            updates = {}
            
            for field, new_value in new_data.items():
                current_value = getattr(deal, field, None)
                
                # Handle None/null comparisons carefully
                if self._values_differ(current_value, new_value):
                    changed_fields.append(field)
                    updates[field] = new_value
            
            if updates:
                # Only update if there are actual changes
                for field, value in updates.items():
                    setattr(deal, field, value)
                
                # Save with only the changed fields
                deal.save(update_fields=list(updates.keys()))
                logger.info(f"Updated deal {record_id} - changed fields: {', '.join(changed_fields)}")
                return True
            else:
                logger.debug(f"No changes detected for deal {record_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving deal {record.get('id')}: {str(e)}")
            raise
    
    def _values_differ(self, current, new):
        """Check if two values are different, handling None/null cases."""
        # Handle None cases
        if current is None and new is None:
            return False
        if current is None or new is None:
            return True
        
        # Handle datetime comparisons (timezone-aware)
        if isinstance(current, datetime) and isinstance(new, datetime):
            return current != new
        
        # Handle string comparisons (strip whitespace)
        if isinstance(current, str) and isinstance(new, str):
            return current.strip() != new.strip()
        
        # Default comparison
        return current != new
    
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
