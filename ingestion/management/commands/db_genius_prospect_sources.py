"""
Django management command for syncing Genius prospect sources using the standardized sync engine.
This command follows the CRM sync guide patterns for consistent data synchronization.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from ingestion.sync.genius.engines.prospect_sources import GeniusProspectSourcesSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Genius prospect sources data using the standardized sync engine'

    def add_arguments(self, parser):
        """Add command arguments following CRM sync guide standards"""
        
        # Core sync flags (distinct purposes)
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp) - fetches ALL records'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Completely replace existing records - enables force overwrite mode'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without actually updating the database'
        )
        
        parser.add_argument(
            '--since',
            type=str,
            help='Sync records modified since this timestamp (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
        )
        
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for date range sync (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
        )
        
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for date range sync (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
        )
        
        parser.add_argument(
            '--max-records',
            type=int,
            help='Maximum number of records to process (for testing/debugging)'
        )
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging for detailed sync information'
        )

    def parse_datetime_arg(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string argument"""
        if not date_str:
            return None
            
        # Try parsing as datetime first, then as date
        try:
            parsed = parse_datetime(date_str)
            if parsed:
                return parsed
                
            # If no time component, try parsing as date and add time
            from django.utils.dateparse import parse_date
            date_obj = parse_date(date_str)
            if date_obj:
                return datetime.combine(date_obj, datetime.min.time())
                
            raise ValueError(f"Could not parse datetime: {date_str}")
        except Exception as e:
            raise ValueError(f"Invalid datetime format '{date_str}': {e}")

    def handle(self, *args, **options):
        """Main command handler"""
        
        # Set up logging
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
            self.stdout.write("🐛 DEBUG MODE - Verbose logging enabled")
        
        # Handle dry run
        if options['dry_run']:
            self.stdout.write("🔍 DRY RUN MODE - No database changes will be made")
        
        # Handle flag combinations
        if options.get('full') and options.get('force'):
            self.stdout.write("🚀 FULL SYNC + FORCE OVERWRITE MODE - Fetching all records and replacing existing data")
        elif options.get('full'):
            self.stdout.write("📊 FULL SYNC MODE - Fetching all records but respecting existing data")
        elif options.get('force'):
            self.stdout.write("💪 FORCE OVERWRITE MODE - Replacing existing records with fetched data")
        
        # Parse datetime arguments
        since = self.parse_datetime_arg(options.get('since'))
        start_date = self.parse_datetime_arg(options.get('start_date'))
        end_date = self.parse_datetime_arg(options.get('end_date'))
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date cannot be after end date")
        
        # Execute sync
        try:
            result = asyncio.run(self.execute_async_sync(
                full=options.get('full', False),
                force=options.get('force', False),
                since=since,
                start_date=start_date,
                end_date=end_date,
                max_records=options.get('max_records'),
                dry_run=options.get('dry_run', False),
                debug=options.get('debug', False)
            ))
            
            # Display results - result is the stats dict directly
            stats = result
            self.stdout.write("✅ Sync completed successfully:")
            self.stdout.write(f"   📊 Processed: {stats.get('total_processed', 0)} records")
            self.stdout.write(f"   ➕ Created: {stats.get('created', 0)} records")
            self.stdout.write(f"   📝 Updated: {stats.get('updated', 0)} records")
            self.stdout.write(f"   ❌ Errors: {stats.get('errors', 0)} records")
            self.stdout.write(f"   ⏭️ Skipped: {stats.get('skipped', 0)} records")
            self.stdout.write(f"   🆔 SyncHistory ID: {stats.get('sync_history_id', 'None')}")
            
        except Exception as e:
            logger.exception("Genius prospect sources sync failed")
            self.stdout.write(
                self.style.ERROR(f"❌ Sync failed: {str(e)}")
            )
            raise

    async def execute_async_sync(self, **kwargs):
        """Execute the async sync operation"""
        engine = GeniusProspectSourcesSyncEngine()
        return await engine.execute_sync(**kwargs)

