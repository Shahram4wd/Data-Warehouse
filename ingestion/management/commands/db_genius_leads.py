"""
Django management command for syncing Genius leads using the new sync engine architecture.
This command follows the CRM sync guide patterns for consistent data synchronization.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from ingestion.sync.genius.engines.leads import GeniusLeadsSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Genius leads data using the standardized sync engine'

    def add_arguments(self, parser):
        """Add command arguments following CRM sync guide standards"""
        
        # Core sync options
        parser.add_argument(
            '--full',
            action='store_true',
            help='Force full sync instead of incremental (ignores last sync timestamp)'
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
        
        # Legacy argument support (deprecated)
        parser.add_argument(
            '--force',
            action='store_true',
            help='DEPRECATED: Use --full instead. Forces full sync ignoring timestamps.'
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
        
        # Handle legacy arguments
        if options.get('force_overwrite'):
            self.stdout.write(
                self.style.WARNING("⚠️  --force-overwrite is deprecated, use --full instead")
            )
            options['full'] = True
        
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
                since=since,
                start_date=start_date,
                end_date=end_date,
                max_records=options.get('max_records'),
                dry_run=options.get('dry_run', False),
                debug=options.get('debug', False)
            ))
            
            # Display results
            if isinstance(result, dict) and 'stats' in result:
                stats = result['stats']
            else:
                # Direct stats return from engine
                stats = result
                
            self.stdout.write("✅ Sync completed successfully:")
            self.stdout.write(f"   📊 Processed: {stats.get('total_processed', 0)} records")
            self.stdout.write(f"   ➕ Created: {stats.get('created', 0)} records")
            self.stdout.write(f"   📝 Updated: {stats.get('updated', 0)} records")
            self.stdout.write(f"   ❌ Errors: {stats.get('errors', 0)} records")
            self.stdout.write(f"   ⏭️ Skipped: {stats.get('skipped', 0)} records")
            
            # Handle sync_id if available
            if isinstance(result, dict) and 'sync_id' in result:
                self.stdout.write(f"   🆔 SyncHistory ID: {result['sync_id']}")
            else:
                self.stdout.write(f"   🆔 SyncHistory ID: None")
            
        except Exception as e:
            logger.exception("Genius leads sync failed")
            self.stdout.write(
                self.style.ERROR(f"❌ Sync failed: {str(e)}")
            )
            raise

    async def execute_async_sync(self, **kwargs):
        """Execute the async sync operation"""
        engine = GeniusLeadsSyncEngine()
        return await engine.execute_sync(**kwargs)

